import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np
from functools import reduce
from django.db.models import Q, Count, Sum, Max, Min, Avg
import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict

from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import IntReceipt, IRPhoto
from .serializers import IntReceiptSerializer
from .filters import IntReceiptFilter
from apps.utils.geography.models import City, District
from apps.int.intaccount.models import IntAccount, Currency
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from ut3.settings import EXPORT_TOPLIMIT
from apps.int.intstatement.models import IntStatement
from apps.int.intpurchase.models import IntPurchaseOrder
from apps.utils.oss.aliyunoss import AliyunOSS


class IntReceiptCreateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_user_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        queryset = IntReceipt.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["creator"] = user.username
        params["order_status"] = 1
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        user = self.request.user
        params["creator"] = user.username
        if all_select_tag:
            handle_list = IntReceiptFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntReceipt.objects.filter(id__in=order_ids, order_status=1, creator=user.username)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.amount == 0:
                    data["error"].append("%s收款金额为0" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue

                obj.remaining = obj.amount

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可取消的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            "流水号": "bank_sn",
            "付款账号": "account",
            "交易日期": "trade_time",
            "币种": "currency",
            "贷方金额": "amount",
            "对方账号": "payment_account_id",
            "对方户名": "payment_account",
            "备注": "memorandum"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:

            df = pd.read_excel(_file, sheet_name=0, dtype=str, skiprows=3)

            FILTER_FIELDS = ["流水号", "付款账号", "交易日期", "币种", "贷方金额", "对方账号", "对方户名", "备注"]

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = IntReceipt.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)

            # 更改一下DataFrame的表名称
            num_end = 0
            step = 300
            step_num = int(len(df) / step) + 2
            i = 1
            while i < step_num:
                num_start = num_end
                num_end = step * i
                intermediate_df = df.iloc[num_start: num_end]

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                _ret_list = intermediate_df.to_dict(orient='records')
                intermediate_report_dic = self.save_resources(request, _ret_list)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource):
        # 设置初始报告
        category_dic = {
            '存入': 1,
            '支出': 2
        }
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:
            row["amount"] = str(row["amount"]).replace(",", "")
            if float(row["amount"]) == 0:
                report_dic["discard"] += 1
                report_dic["error"].append("%s 不是收款业务" % row["bank_sn"])
                continue
            order_fields = ["bank_sn", "account", "trade_time", "currency", "amount", "payment_account_id",
                            "payment_account", "memorandum"]
            if not row["bank_sn"]:
                report_dic["error"].append("%s 无流水号" % row["payment_account"])
                report_dic["false"] += 1
                continue
            if row["trade_time"]:
                row["trade_time"] = datetime.datetime.strptime(row["trade_time"], "%Y%m%d")
            else:
                report_dic["error"].append("%s 无交易时间" % row["payment_account"])
                report_dic["false"] += 1
                continue
            if row["currency"]:
                _q_currency = Currency.objects.filter(name=row["currency"])
                if _q_currency.exists():
                    row["currency"] = _q_currency[0]
                else:
                    report_dic["error"].append("%s UT无此币种" % row["payment_account"])
                    report_dic["false"] += 1
                    continue
            if row["account"]:
                _q_intacount = IntAccount.objects.filter(a_id=row["account"], currency=row["currency"])
                if _q_intacount.exists():
                    row["account"] = _q_intacount[0]
                else:
                    report_dic["error"].append("%s UT无此收款账号" % row["payment_account"])
                    report_dic["false"] += 1
                    continue
            _q_order_exists = IntReceipt.objects.filter(bank_sn=row["bank_sn"])
            if _q_order_exists.exists():
                order = _q_order_exists[0]
                if order.order_status != 1:
                    report_dic["error"].append("%s 重复创建" % order.bank_sn)
                    report_dic["false"] += 1
                    continue
            else:
                order = IntReceipt()
            for field in order_fields:
                setattr(order, field, row[field])
            order.category = 1

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["payment_account"])
                report_dic["false"] += 1
                continue
            if not order.order_id:
                number = int(order.id) + 10000000
                profix = "COD"
                order.order_id = '%s%s' % (profix, str(number)[-7:])
                order.save()
        return report_dic

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = IntReceipt.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/int/receipt"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = IRPhoto()
                photo_order.url = obj["url"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class IntReceiptSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_handler_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        queryset = IntReceipt.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = IntReceiptFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntReceipt.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }

        if n:
            for obj in check_list:

                if not obj.handler:
                    data["error"].append("%s 必须先认领才可以审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                if obj.handler != request.user.username:
                    data["error"].append("%s 只有认领人才可以审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                if obj.is_received:
                    obj.order_status = 4
                else:
                    obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                obj.order_status = 1
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def confirm(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if id:
            order = IntReceipt.objects.filter(id=id)[0]
            order.handler = request.user.username
            order.handle_time = datetime.datetime.now()
            start_time = datetime.datetime.strptime(str(order.create_time).split(".")[0],
                                                    "%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.strptime(str(order.handle_time).split(".")[0],
                                                  "%Y-%m-%d %H:%M:%S")
            d_value = end_time - start_time
            days_seconds = d_value.days * 3600
            total_seconds = days_seconds + d_value.seconds
            order.services_interval = math.floor(total_seconds / 60)
            order.save()

        else:
            raise serializers.ValidationError("没有可认领的单据！")
        data["successful"] = 1
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_confirm(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if id:
            order = IntReceipt.objects.filter(id=id)[0]
            order.handler = ''
            order.save()
        else:
            raise serializers.ValidationError("没有可认领的单据！")
        data["successful"] = 1
        return Response(data)

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = IntReceipt.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/int/receipt"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = IRPhoto()
                photo_order.url = obj["url"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class IntReceiptCheckViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_handler_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        queryset = IntReceipt.objects.filter(order_status=3).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 3
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = IntReceiptFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntReceipt.objects.filter(id__in=order_ids, order_status=3)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if not obj.is_received:
                    data["error"].append("%s 未到账不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue

                obj.order_status = 4
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                obj.order_status = 2
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            '店铺': 'shop',
            '客户网名': 'nickname',
            '收件人': 'receiver',
            '地址': 'address',
            '手机': 'mobile',
            '货品编码': 'goods_id',
            '数量': 'quantity',
            '单据类型': 'order_category',
            '机器序列号': 'm_sn',
            '故障部位': 'broken_part',
            '故障描述': 'description',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["店铺", "客户网名", "收件人", "地址", "手机", "货品编码", "货品名称", "数量", "单据类型",
                             "机器序列号", "故障部位", "故障描述"]

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = ManualOrder.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)

            # 更改一下DataFrame的表名称
            num_end = 0
            step = 300
            step_num = int(len(df) / step) + 2
            i = 1
            while i < step_num:
                num_start = num_end
                num_end = step * i
                intermediate_df = df.iloc[num_start: num_end]

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                _ret_list = intermediate_df.to_dict(orient='records')
                intermediate_report_dic = self.save_resources(request, _ret_list)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource):
        # 设置初始报告
        category_dic = {
            '质量问题': 1,
            '开箱即损': 2,
            '礼品赠品': 3
        }
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:

            order_fields = ["nickname", "receiver", "address", "mobile", "m_sn", "broken_part", "description"]
            order = ManualOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            order.order_category = category_dic.get(row["order_category"], None)
            _q_shop =  Shop.objects.filter(name=row["shop"])
            if _q_shop.exists():
                order.shop = _q_shop[0]

            _spilt_addr = PickOutAdress(str(order.address))
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                report_dic["error"].append("%s 地址无法提取省市区" % order.address)
                report_dic["false"] += 1
                continue
            cs_info_fields = ["province", "city", "district", "address"]
            for key_word in cs_info_fields:
                setattr(order, key_word, _rt_addr.get(key_word, None))

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
            goods_details = MOGoods()
            goods_details.manual_order = order
            goods_details.quantity = row["quantity"]
            _q_goods = Goods.objects.filter(goods_id=row["goods_id"])
            if _q_goods.exists():
                goods_details.goods_name = _q_goods[0]
                goods_details.goods_id = row["goods_id"]
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic


class IntReceiptExecuteViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_handler_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        user = self.request.user
        queryset = IntReceipt.objects.filter(order_status=4, handler=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 4
        params["handler"] = user.username
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 4
        params["handler"] = user.username
        if all_select_tag:
            handle_list = IntReceiptFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntReceipt.objects.filter(id__in=order_ids, order_status=4)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                statement_details = obj.intstatement_set.filter(order_status=1)
                try:
                    associated_amount = statement_details.aggregate(Sum("actual_amount"))["actual_amount__sum"]
                except Exception as e:
                    associated_amount = 0
                if not associated_amount:
                    associated_amount = 0

                if obj.remaining != associated_amount:
                    data["error"].append("%s 可分配金额有余额，不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                obj.remaining = 0
                for statement in statement_details:
                    statement.ipo.actual_amount = statement.actual_amount
                    statement.ipo.virtual_amount = statement.virtual_amount
                    if statement.ipo.virtual_amount < statement.ipo.amount:
                        statement.ipo.collection_status = 1
                    else:
                        statement.ipo.collection_status = 2
                    statement.ipo.save()
                    statement.order_status = 2
                    statement.save()
                obj.order_status = 5
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                obj.order_status = 3
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    def check_statements(self, statements):
        for statement in statements:
            if not all([statement.get("ipo", None), statement.get("actual_amount", None), statement.get("virtual_amount", None)]):
                raise serializers.ValidationError("明细中采购单、实收金额和销减金额为必填项！")
        ipo_list = list(map(lambda x: x["ipo"], statements))
        ipo_check = set(ipo_list)
        if len(ipo_list) != len(ipo_check):
            raise serializers.ValidationError("明细中采购单重复, 一张收款单不可重复关联一个采购单！")
        actual_amount_list = list(map(lambda x: x['actual_amount'], statements))
        virtual_amount_list = list(map(lambda x: x['virtual_amount'], statements))
        data = {
            "actual_amount_total": reduce(lambda x, y: x + y, actual_amount_list),
            "virtual_amount_total": reduce(lambda x, y: x + y, virtual_amount_list)
        }
        return data

    @action(methods=['patch'], detail=False)
    def create_statement(self, request, *args, **kwargs):
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        receipt = request.data
        total_amount = self.check_statements(receipt["statements"])
        if int(total_amount["actual_amount_total"]) > int(receipt["remaining"]):
            raise serializers.ValidationError({"金额错误": "采购单实收金额超过收款单可拆金额！"})
        receipt_order = IntReceipt.objects.filter(id=receipt["id"])[0]
        account = IntAccount.objects.filter(id=receipt["account"])[0]
        r_currency = receipt["currency"]
        for statement in receipt["statements"]:
            ipo = IntPurchaseOrder.objects.filter(id=statement["ipo"])[0]
            if r_currency["id"] != ipo.currency.id:
                raise serializers.ValidationError({"采购单币种错误": "采购单和收款单币种不同！"})
            if (ipo.amount - ipo.virtual_amount) < int(statement["virtual_amount"]):
                raise serializers.ValidationError({"结算单金额错误": "销账金额超出采购单合同金额！"})
            if statement.actual_amount / statement.virtual_amount < 0.9:
                raise serializers.ValidationError({"结算单金额错误": "销账金额和实收金额比例错误！"})
            _q_statement = IntStatement.objects.filter(ipo=ipo, receipt=receipt_order)
            if _q_statement.exists():
                check_order = _q_statement[0]
                if check_order.order_status in [0, 1]:
                    order = check_order
                else:
                    data["error"].append("%s 收款单已关联过此采购单！" % ipo.order_id)
                    data["false"] += 1
                    continue
            else:
                order = IntStatement()

            order.ipo = ipo
            order.receipt = receipt_order
            order.account = account
            order_fields = ["actual_amount", "virtual_amount", "memorandum"]
            for keyword in order_fields:
                setattr(order, keyword, statement.get(keyword, None))
            order.creator = request.user.username
            try:
                order.save()
                data["successful"] += 1
            except Exception as e:
                data["error"].append("结算单创建出错：%s " % e)
                data["false"] += 1
                continue
        return Response(data)


class IntReceiptBalanceViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_handler_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        queryset = IntReceipt.objects.filter(order_status=5).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 5
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 5
        if all_select_tag:
            handle_list = IntReceiptFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntReceipt.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        if n:
            for obj in check_list:
                _q_mo_repeat = ManualOrder.objects.filter(erp_order_id=obj.erp_order_id)
                if _q_mo_repeat.exists():
                    order = _q_mo_repeat[0]
                    if order.order_status in [0, 1]:
                        order.order_status = 1
                        order.mogoods_set.all().delete()
                    else:
                        data["error"].append("%s重复递交" % obj.id)
                        n -= 1
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                else:
                    order = ManualOrder()
                    order.erp_order_id = obj.erp_order_id

                if obj.order_category in [1, 2]:
                    if not all([obj.m_sn, obj.broken_part, obj.description]):
                        data["error"].append("%s售后配件需要补全sn、部件和描述" % obj.id)
                        n -= 1
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                if not obj.department:
                    data["error"].append("%s无部门" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                if not all([obj.province, obj.city]):
                    data["error"].append("%s省市不可为空" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                if obj.city.name not in special_city and not obj.district:
                    data["error"].append("%s 区县不可为空" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                if not re.match(r"^((0\d{2,3}-\d{7,8})|(1[3456789]\d{9}))$", obj.mobile):
                    data["error"].append("%s 手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                if not obj.shop:
                    data["error"].append("%s 无店铺" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                if '集运' in str(obj.address):
                    data["error"].append("%s地址是集运仓" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                order_fields = ["nickname", "receiver", "address", "mobile", "m_sn", "broken_part", "description",
                                "erp_order_id", "shop", "province", "city", "district", "order_id", "order_category",
                                "creator"]
                for keyword in order_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.department = request.user.department
                try:
                    order.save()
                except Exception as e:
                    data["error"].append("%s 手工单保存出错" % obj.order_id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                error_tag = 0
                all_goods_details = obj.dpgoods_set.all()
                for goods_detail in all_goods_details:
                    _q_dp_repeat = DPGoods.objects.filter(dealer_parts__mobile=obj.mobile, goods_id=goods_detail.goods_id).order_by("-create_time")
                    if len(_q_dp_repeat) > 1:
                        if obj.process_tag != 3:
                            delta_date = (obj.create_time - _q_dp_repeat[1].create_time).days
                            if int(delta_date) < 14:
                                error_tag = 1
                                data["error"].append("%s 14天内重复" % obj.id)
                                n -= 1
                                obj.mistake_tag = 8
                                obj.save()
                                break
                            else:
                                error_tag = 1
                                data["error"].append("%s 14天外重复" % obj.id)
                                n -= 1
                                obj.mistake_tag = 9
                                obj.save()
                                break
                    mo_detail = MOGoods()
                    mo_detail.manual_order = order
                    detail_goods_fields = ["goods_name", "goods_id", "quantity", "creator"]
                    for keyword in detail_goods_fields:
                        setattr(mo_detail, keyword, getattr(goods_detail, keyword, None))
                    try:
                        mo_detail.save()
                        goods_detail.order_status = 2
                        goods_detail.save()
                    except Exception as e:
                        error_tag = 1
                        data["error"].append("%s 手工单货品保存出错" % obj.id)
                        n -= 1
                        obj.mistake_tag = 11
                        obj.save()
                        break
                if error_tag:
                    continue
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                obj.order_status = 4
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class IntReceiptManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定收款单
    list:
        返回收款单明细
    update:
        更新收款单明细
    destroy:
        删除收款单明细
    create:
        创建收款单明细
    partial_update:
        更新部分收款单明细
    """
    serializer_class = IntReceiptSerializer
    filter_class = IntReceiptFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return IntReceipt.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = IntReceipt.objects.all().order_by("-id")
        else:
            queryset = IntReceipt.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):

        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        user = request.user
        if user.is_our:
            params["creator"] = user.username
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)
