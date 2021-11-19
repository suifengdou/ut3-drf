import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np

import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict

from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import OriginData, BatchTable
from .serializers import OriginDataSerializer, BatchTableSerializer
from .filters import OriginDataFilter, BatchTableFilter
from apps.utils.geography.models import Province, City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.utils.geography.tools import PickOutAdress



class OriginDataSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = OriginDataSerializer
    filter_class = OriginDataFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['batchtable.view_origindata', ]
    }

    def get_queryset(self):
        if not self.request:
            return OriginData.objects.none()
        queryset = OriginData.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriginDataFilter(params)
        serializer = OriginDataSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriginDataFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriginData.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:
                if order.src_tids:
                    if not all([order.return_express_company, order.return_express_id]):
                        order.mistake_tag = 1
                        data["error"].append("%s 返回单号或快递为空" % order.order_id)
                        order.save()
                        n -= 1
                        continue
                order.order_status = 2
                order.mistake_tag = 0
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

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

                if obj.erp_order_id:
                    _q_repeat_order = ManualOrder.objects.filter(erp_order_id=obj.erp_order_id)
                    if _q_repeat_order.exists():
                        order = _q_repeat_order[0]
                        if order.order_status == 0:
                            order.order_status = 1
                        elif order.order_status == 1:
                            _q_goods_name = MOGoods.objects.filter(manual_order=order, goods_name=obj.goods_name)
                            if _q_goods_name.exists():
                                data["error"].append("%s重复递交，已存在输出单据" % obj.id)
                                n -= 1
                                obj.mistake_tag = 4
                                obj.save()
                                continue
                        else:
                            data["error"].append("%s重复递交，已存在输出单据" % obj.id)
                            n -= 1
                            obj.mistake_tag = 4
                            obj.save()
                            continue
                    else:
                        order = ManualOrder()
                else:
                    order =  ManualOrder()
                    _prefix = "BO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                order.order_category = 3

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                if not re.match(r"^1[3456789]\d{9}$", obj.mobile):
                    data["error"].append("%s 手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue
                if '集运' in str(obj.address):
                    data["error"].append("%s地址是集运仓" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue

                order_fields = ["shop", "nickname", "receiver", "mobile", "erp_order_id", "order_id"]
                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))

                try:
                    order.memo = obj.buyer_remark
                    order.department = request.user.department
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data["error"].append("%s输出单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                order_detail = MOGoods()
                detail_fields = ["goods_name", "goods_id", "quantity"]
                for detail_field in detail_fields:
                    setattr(order_detail, detail_field, getattr(obj, detail_field, None))
                try:
                    order_detail.memorandum = obj.buyer_remark
                    order_detail.manual_order = order
                    order_detail.creator = request.user.username
                    order_detail.save()
                except Exception as e:
                    data["error"].append("%s输出单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                obj.submit_user = request.user.username
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 1
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

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)
            columns_key_ori = df.columns.values.tolist()
            filter_fields = ["店铺", "店铺名称", "订单号", "订单编号", "销售订单号", "下单帐号", "买家会员名", "ID",
                             "客户网名", "用户昵称", "网名", "客户姓名", "收货人姓名", "姓名", "顾客姓名", "收件人", "发布平台ID",
                             "收货人", "客户地址", "收货地址 ", "收货地址","地址", "送货地址", "收件地址", "派送地址", "家庭地址",
                             "联系电话", "联系手机", "手机号", "顾客联系方式", "手机", "赠品名称", "数量", "买家留言", "买家备注"]
            INIT_FIELDS_DIC = {
                "店铺": "shop",
                "店铺名": "shop",
                "店铺名称": "shop",
                "订单号": "order_id",
                "订单编号": "order_id",
                "销售订单号": "order_id",
                "下单帐号": "nickname",
                "买家会员名": "nickname",
                "发布平台ID": "nickname",
                "ID": "nickname",
                "客户网名": "nickname",
                "用户昵称": "nickname",
                "网名": "nickname",
                "客户姓名": "receiver",
                "收货人姓名": "receiver",
                "姓名": "receiver",
                "顾客姓名": "receiver",
                "收件人": "receiver",
                "收货人": "receiver",
                "客户地址": "address",
                "收货地址": "address",
                "地址": "address",
                "送货地址": "address",
                "收件地址": "address",
                "派送地址": "address",
                "家庭地址": "address",
                "联系手机": "mobile",
                "手机号": "mobile",
                "顾客联系方式": "mobile",
                "手机": "mobile",
                "赠品名称": "goods_name",
                "数量": "quantity",
                "买家留言": "buyer_remark",
                "买家备注": "buyer_remark"
            }
            result_keys = []
            for keywords in columns_key_ori:
                if keywords in filter_fields:
                    result_keys.append(keywords)

            try:
                df = df[result_keys]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            result_columns = []
            for keywords in columns_key:
                result_columns.append(INIT_FIELDS_DIC.get(keywords, None))

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = OriginData.verify_mandatory(result_columns)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            ret_columns_key = dict(zip(columns_key, result_columns))
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
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        _q_shop = Shop.objects.filter(name=resource[0]["shop"])
        if _q_shop.exists():
            shop = _q_shop[0]
        else:
            report_dic["error"].append("店铺名称错误")
            return report_dic
        for row in resource:

            order_fields = ["nickname", "receiver", "address", "mobile", "order_id", "quantity", "buyer_remark"]
            order = OriginData()
            for field in order_fields:
                setattr(order, field, row[field])
            order.mobile = re.sub("[a-zA-Z!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.mobile))
            order.shop = shop
            _q_goods_name = Goods.objects.filter(name=row["goods_name"])
            if _q_goods_name.exists():
                order.goods_name = _q_goods_name[0]
                order.goods_id = order.goods_name.goods_id
            else:
                report_dic["false"] += 1
                report_dic["error"].append("%s 货品名称错误" % row["order_id"])
                continue
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1

        return report_dic


class OriginDataManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = OriginDataSerializer
    filter_class = OriginDataFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['batchtable.view_origindata', ]
    }

    def get_queryset(self):
        if not self.request:
            return OriginData.objects.none()
        queryset = OriginData.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = OriginDataFilter(params)
        serializer = OriginDataSerializer(f.qs, many=True)
        return Response(serializer.data)


class BatchTableSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = BatchTableSerializer
    filter_class = BatchTableFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['batchtable.view_batchtable', ]
    }

    def get_queryset(self):
        if not self.request:
            return BatchTable.objects.none()
        queryset = BatchTable.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = BatchTableFilter(params)
        serializer = BatchTableSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = BatchTableFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BatchTable.objects.filter(id__in=order_ids, order_status=1)
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
                special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市',
                                '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                                '白沙黎族自治县', '中山市', '东莞市']
                export_order = BatchTable()
                if obj.order_category in [1, 2]:
                    if not all([obj.m_sn, obj.broken_part, obj.description]):
                        data["error"].append("%s售后配件需要补全sn、部件和描述" % obj.id)
                        n -= 1
                        obj.mistakes = 10
                        obj.save()
                        continue
                if not all([obj.province, obj.city]):
                    data["error"].append("%s省市不可为空" % obj.id)
                    n -= 1
                    obj.mistakes = 4
                    obj.save()
                    continue
                if obj.city.name not in special_city and not obj.district:
                    data["error"].append("%s 区县不可为空" % obj.id)
                    n -= 1
                    obj.mistakes = 4
                    obj.save()
                    continue
                if not re.match(r"^((0\d{2,3}-\d{7,8})|(1[34578]\d{9}))$", obj.mobile):
                    data["error"].append("%s 手机错误" % obj.id)
                    n -= 1
                    obj.mistakes = 7
                    obj.save()
                    continue
                if not obj.shop:
                    data["error"].append("%s 无店铺" % obj.id)
                    n -= 1
                    obj.mistakes = 9
                    obj.save()
                    continue
                if '集运' in str(obj.address):
                    data["error"].append("%s地址是集运仓" % obj.id)
                    n -= 1
                    obj.mistakes = 8
                    obj.save()
                    continue
                _prefix = "MO"
                serial_number = str(datetime.date.today()).replace("-", "")
                obj.erp_order_id = serial_number + _prefix + str(obj.id)
                error_tag = 0
                all_goods_details = obj.mogoods_set.all()
                for goods_detail in all_goods_details:
                    _q_export_mo = BatchTable.objects.filter(mobile=obj.mobile, goods_id=goods_detail.goods_id)
                    if _q_export_mo.exists():
                        if obj.process_tag != 3:
                            delta_date = (obj.create_time - _q_export_mo[0].create_time).days
                            if int(delta_date) < 14:
                                error_tag = 1
                                data["error"].append("%s14天内重复" % obj.order_id)
                                n -= 1
                                obj.mistakes = 2
                                obj.save()
                                break
                            else:
                                error_tag = 1
                                data["error"].append("%s14天外重复" % obj.order_id)
                                n -= 1
                                obj.mistakes = 2
                                obj.save()
                                break
                    if not export_order.goods_id:
                        export_order.goods_id = goods_detail.goods_id
                        export_order.goods_name = goods_detail.goods_name.name
                        export_order.quantity = goods_detail.quantity
                        export_order.buyer_remark = "%s %s 创建" % (obj.department.name, obj.creator)
                    goods_info = "+ %s*%s" % (goods_detail.goods_name.name, goods_detail.quantity)
                    goods_id_info = "+ %s*%s" % (goods_detail.goods_id, goods_detail.quantity)
                    export_order.buyer_remark = str(export_order.buyer_remark) + goods_info
                    export_order.cs_memoranda = str(export_order.cs_memoranda) + goods_id_info
                if error_tag:
                    continue
                order_fields = ["shop", "nickname", "receiver", "address", "mobile", "province", "city", "district",
                                "erp_order_id"]
                for field in order_fields:
                    setattr(export_order, field, getattr(obj, field, None))
                try:
                    export_order.creator = request.user.username
                    export_order.save()
                except Exception as e:
                    data["error"].append("%s输出单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.mistakes = 5
                    obj.save()
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 1
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
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class BatchTableManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = BatchTableSerializer
    filter_class = BatchTableFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['batchtable.view_batchtable', ]
    }

    def get_queryset(self):
        if not self.request:
            return BatchTable.objects.none()
        queryset = BatchTable.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = BatchTableFilter(params)
        serializer = BatchTableSerializer(f.qs, many=True)
        return Response(serializer.data)

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
            _ret_verify_field = BatchTable.verify_mandatory(columns_key)
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
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        jieba.load_userdict("apps/dfc/manualorder/addr_key_words.txt")
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        for row in resource:

            order_fields = ["nickname", "receiver", "address", "mobile", "order_id"]
            order = BatchTable()
            for field in order_fields:
                setattr(order, field, row[field])
            order.order_category = category_dic.get(row["order_category"], None)
            _q_shop = Shop.objects.filter(name=row["shop"])
            if _q_shop.exists():
                order.shop = _q_shop[0]
            address = re.sub("[0-9!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.address))
            seg_list = jieba.lcut(address)
            for words in seg_list:
                if not order.city:
                    _q_city = City.objects.filter(name__contains=words)
                    if not _q_city.exists():
                        _q_city_again = City.objects.filter(name__contains=words[:2])
                        if not _q_city_again.exists():
                            continue
                        else:
                            order.city = _q_city_again[0]
                    else:
                        order.city = _q_city[0]
                else:

                    if order.city.name in special_city:
                        break
                    _q_district = District.objects.filter(name__contains=words)
                    if not _q_district:
                        continue
                    else:
                        order.district = _q_district[0]
                        break

            if order.city:
                order.province = order.city.province

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1

        return report_dic



