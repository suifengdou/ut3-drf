import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np
import copy
from functools import reduce

import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict
from ut3.settings import EXPORT_TOPLIMIT
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from django.db.models import Sum, F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from apps.base.warehouse.models import Warehouse
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from .models import RefundTrialOrder, RTOGoods, LogRefundTrialOrder, LogRTOGoods
from .filters import RefundTrialOrderFilter, RTOGoodsFilter
from .serializers import RefundTrialOrderSerializer, RTOGoodsSerializer
from apps.dfc.manualorder.models import ManualOrder, MOGoods, ManualOrderExport, LogManualOrder, LogManualOrderExport, MOFiles, LogMOGoods
from apps.dfc.manualorder.serializers import ManualOrderSerializer, MOGoodsSerializer
from apps.dfc.manualorder.filters import ManualOrderFilter, MOGoodsFilter
from apps.utils.logging.loggings import getlogs, logging
from apps.psi.outbound.models import Outbound, OutboundDetail, LogOutbound, LogOutboundDetail
from apps.psi.inbound.models import Inbound, InboundDetail, LogInbound, LogInboundDetail
from apps.utils.oss.aliyunoss import AliyunOSS
from apps.psi.inventory.models import IORelation
from apps.crm.customers.models import Customer, LogCustomer
from apps.crm.csaddress.models import CSAddress, LogCSAddress
from apps.psi.logistics.views import CreateLogisticOrder, Logistics


class TrialOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = ManualOrderSerializer
    filter_class = ManualOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return ManualOrder.objects.none()
        department = self.request.user.department
        queryset = ManualOrder.objects.filter(order_status=1, order_category=4, department=department, process_tag=0).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["department"] = user.department
        params["order_status"] = 1
        params["order_category"] = 4
        params["process_tag"] = 0
        f = ManualOrderFilter(params)
        serializer = ManualOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        department = self.request.user.department
        params["department"] = department
        params["order_category"] = 4
        params["process_tag"] = 0
        if all_select_tag:
            handle_list = ManualOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ManualOrder.objects.filter(id__in=order_ids, order_status=1, department=department, process_tag=0)
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
        user = request.user
        warehouse = Warehouse.objects.filter(name="北京体验仓")[0]
        if n:
            for obj in check_list:
                if not obj.erp_order_id:
                    _prefix = "SSTO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = _prefix + serial_number + str(obj.id)
                    obj.save()
                if not obj.warehouse:
                    obj.warehouse = warehouse
                    obj.save()
                    if "体验" in str(obj.warehouse.name):
                        data["error"].append("%s 仓库非体验仓无法提交" % obj.id)
                        n -= 1
                        obj.mistake_tag = 18
                        obj.save()
                        continue
                all_goods_details = obj.mogoods_set.all()
                if not all_goods_details.exists():
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 15
                    obj.save()
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status > 1:
                        data["error"].append("%s 关联出库单错误，联系管理员" % obj.id)
                        n -= 1
                        obj.mistake_tag = 16
                        obj.save()
                        continue
                    else:
                        outbound.order_status = 1
                else:
                    outbound = Outbound()
                    suffix = str(datetime.datetime.now().date()).replace("-", "")
                    outbound.code = f"ODO{suffix}"
                outbound.warehouse = obj.warehouse
                outbound.verification = obj.erp_order_id

                try:
                    outbound.creator = user.username
                    outbound.save()
                    outbound.code = f'{outbound.code}-{outbound.id}'
                    outbound.save()
                    logging(outbound, user, LogOutbound, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id} 关联出库单创建错误：{e}")
                    n -= 1
                    obj.mistake_tag = 17
                    obj.save()
                    continue
                outbound.outbounddetail_set.all().delete()
                for goods in all_goods_details:
                    outbound_goods_dict = {
                        "order": outbound,
                        "goods": goods.goods_name,
                        "code": outbound.code,
                        "category": 1,
                        "warehouse": obj.warehouse,
                        "quantity": goods.quantity,
                        "price": goods.price,
                        "memo": goods.memorandum,
                    }
                    outbound_goods = OutboundDetail.objects.create(**outbound_goods_dict)
                    outbound_goods.code = f'{outbound_goods.code}-{outbound_goods.id}'
                    outbound_goods.save()
                    logging(outbound_goods, user, LogOutboundDetail, "创建")
                obj.process_tag = 1
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogManualOrder, "递交试用申请")
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=3)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_tag(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=0)
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
            else:
                report_dic["error"].append("%s UT无此货品" % row["goods_id"])
                report_dic["false"] += 1
                continue
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = ManualOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/sales/trialgoods"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = MOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = user.username
                photo_order.save()
                logging(work_order, user, LogManualOrder, f"上传图片{photo_order.name}")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class TrialOrderCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = ManualOrderSerializer
    filter_class = ManualOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return ManualOrder.objects.none()
        department = self.request.user.department
        queryset = ManualOrder.objects.filter(order_status=1, order_category=4, department=department, process_tag=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["department"] = user.department
        params["order_status"] = 1
        params["order_category"] = 4
        params["process_tag"] = 1
        f = ManualOrderFilter(params)
        serializer = ManualOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        department = self.request.user.department
        params["department"] = department
        params["order_category"] = 4
        params["process_tag"] = 1
        if all_select_tag:
            handle_list = ManualOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ManualOrder.objects.filter(id__in=order_ids, order_status=1, department=department, process_tag=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def odotrial(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in set_list:
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id, order_status=1)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    all_goods = outbound.outbounddetail_set.all().filter(order_status=1)
                    if all_goods.exists():
                        error_sign = 0
                        for goods in all_goods:
                            _q_inbounddetail = InboundDetail.objects.filter(goods=goods.goods,
                                                                            warehouse=goods.warehouse, category=1)
                            if _q_inbounddetail.exists():
                                balance = _q_inbounddetail.aggregate(Sum("valid_quantity"))["valid_quantity__sum"]
                                odo_quantity = copy.copy(goods.quantity)
                                if odo_quantity <= 0:
                                    data["error"].append("%s 出库数量错误" % odo_quantity)
                                    n -= 1
                                    obj.mistake_tag = 23
                                    obj.save()
                                    error_sign = 1
                                    break
                                if balance < odo_quantity:
                                    data["error"].append("%s 缺货无法出库" % goods.goods.name)
                                    n -= 1
                                    obj.mistake_tag = 19
                                    obj.save()
                                    error_sign = 1
                                    break

                                for inbounddetail in _q_inbounddetail:
                                    if inbounddetail.valid_quantity > odo_quantity:
                                        inbounddetail.valid_quantity -= odo_quantity
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail,
                                                f"{goods.code}销减库存{goods.quantity}")
                                        goods.order_status = 2
                                        goods.save()
                                        logging(goods, user, LogOutboundDetail, f"关联入库明细{inbounddetail.code}")
                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail, outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = odo_quantity
                                            io_relation.save()
                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": odo_quantity
                                            })
                                        break
                                    else:
                                        io_quantity = copy.copy(inbounddetail.valid_quantity)
                                        odo_quantity -= inbounddetail.valid_quantity
                                        inbounddetail.valid_quantity = 0
                                        inbounddetail.order_status = 4
                                        inbounddetail.is_complelted = True
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail,
                                                f"{goods.code}清账库存销减库存{goods.quantity}")

                                        _q_check_inbound_detail = inbounddetail.order.inbounddetail_set.filter(
                                            order_status=3)
                                        if not _q_check_inbound_detail.exists():
                                            inbounddetail.order.order_status = 4
                                            inbounddetail.order.save()
                                            logging(inbounddetail.order, user, LogInbound, "完结入库单")

                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail,
                                                                                         outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = io_quantity
                                            io_relation.save()

                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": io_quantity
                                            })
                                        if odo_quantity == 0:
                                            goods.order_status = 2
                                            goods.save()
                                            logging(goods, user, LogOutboundDetail,
                                                    f"关联入库明细{inbounddetail.code}并完结出库明细")
                                            _q_check_outbound_detail = goods.order.outbounddetail_set.filter(
                                                order_status=1)
                                            if not _q_check_outbound_detail.exists():
                                                goods.order.order_status = 2
                                                goods.order.save()
                                                logging(goods.order, user, LogOutbound, "完结出库单")
                                            break
                            else:
                                data["error"].append("%s 库存不存在" % goods.goods)
                                n -= 1
                                obj.mistake_tag = 20
                                obj.save()
                                error_sign = 1
                                break
                        if error_sign:
                            continue

                    outbound.order_status = 2
                    outbound.save()
                    logging(outbound, user, LogOutbound, "出库完成")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(set_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def odoreturn(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in set_list:
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id, order_status=2)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    all_goods = outbound.outbounddetail_set.all().filter(order_status=2)
                    if all_goods.exists():
                        for goods in all_goods:
                            _q_io_relation = IORelation.objects.filter(outbound=goods)
                            if _q_io_relation.exists():
                                for io_relation in _q_io_relation:
                                    inbound = io_relation.inbound
                                    outbound = io_relation.outbound
                                    inbound.valid_quantity += io_relation.quantity
                                    if inbound.order_status == 4:
                                        inbound.is_complelted = False
                                        inbound.order_status = 3
                                        inbound.save()
                                        logging(inbound, user, LogInboundDetail, "释放库存")
                                        if inbound.order.order_status == 4:
                                            inbound.order.order_status = 3
                                            inbound.order.save()
                                            logging(inbound.order, user, LogInbound, "释放库存")
                                    outbound.order_status = 1
                                    outbound.save()
                                    logging(outbound, user, LogOutboundDetail, "释放库存")
                                    if outbound.order.order_status == 2:
                                        outbound.order.order_status = 1
                                        outbound.order.save()
                                        logging(outbound.order, user, LogOutbound, "释放库存")
                            else:
                                continue

                else:
                    data["error"].append("%s 未完全锁定库存不可释放" % obj.id)
                    n -= 1
                    obj.mistake_tag = 21
                    obj.save()
                    continue
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(set_list) - n
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
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市', '北屯市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        express_list = {
            1: "顺丰",
            2: "圆通",
            3: "韵达",
        }
        user = request.user
        warehouse = Warehouse.objects.filter(name="北京体验仓")[0]
        if n:
            for obj in check_list:
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id, order_status=1)
                if _q_outbound.exists():
                    data["error"].append("%s未锁定库存" % obj.id)
                    n -= 1
                    obj.mistake_tag = 22
                    obj.save()
                    continue
                if not obj.erp_order_id:
                    _prefix = "MO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                    obj.save()
                _q_mo_exp_repeat = ManualOrderExport.objects.filter(ori_order=obj)
                if _q_mo_exp_repeat.exists():
                    order = _q_mo_exp_repeat[0]
                    if order.order_status in [0, 1]:
                        order.order_status = 1
                        order.buyer_remark = ""
                        order.cs_memoranda = ""
                    else:
                        data["error"].append("%s重复递交" % obj.id)
                        n -= 1
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                else:
                    order = ManualOrderExport()
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
                if not re.match(r"^((0\d{2,3}-\d{7,8})|(1[23456789]\d{9}))$", obj.mobile):
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
                    if obj.process_tag != 3:
                        data["error"].append("%s地址是集运仓" % obj.id)
                        n -= 1
                        obj.mistake_tag = 7
                        obj.save()
                        continue
                if not obj.receiver:
                    data["error"].append("%s 无收件人" % obj.id)
                    n -= 1
                    obj.mistake_tag = 12
                    obj.save()
                    continue

                order.buyer_remark = "%s 的 %s 创建" % (str(obj.department), str(obj.creator))
                if obj.servicer:
                    order.buyer_remark = "%s来自%s" % (order.buyer_remark, str(obj.servicer))
                error_tag = 0
                export_goods_details = []
                all_goods_details = obj.mogoods_set.all()
                if not all_goods_details:
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 11
                    obj.save()
                    continue
                _q_complete_machine = all_goods_details.filter(goods_name__category=1)
                if _q_complete_machine.exists():
                    if not re.match('^SS', obj.erp_order_id):
                        data["error"].append("%s 此类型不可发整机" % obj.id)
                        n -= 1
                        obj.mistake_tag = 13
                        obj.save()
                        continue
                total = all_goods_details.values("quantity").annotate(sum_quantity=Sum("quantity"))[0]["sum_quantity"]
                if total < 1:
                    data["error"].append("%s 货品数量错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 11
                    obj.save()
                    continue
                if len(all_goods_details) > 1:
                    order.cs_memoranda = "#"
                for goods_detail in all_goods_details:
                    _q_mo_repeat = MOGoods.objects.filter(manual_order__mobile=obj.mobile, goods_id=goods_detail.goods_id).order_by("-created_time")
                    if len(_q_mo_repeat) > 1:
                        if obj.process_tag != 3:
                            delta_date = (obj.created_time - _q_mo_repeat[1].created_time).days
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
                    if not export_goods_details:
                        export_goods_details = [goods_detail.goods_name.name, goods_detail.goods_id, goods_detail.quantity]
                    goods_info = "+ %sx%s" % (goods_detail.goods_name.name, goods_detail.quantity)
                    goods_id_info = "+ %s x%s" % (goods_detail.goods_id, goods_detail.quantity)
                    order.buyer_remark = str(order.buyer_remark) + goods_info
                    order.cs_memoranda = str(order.cs_memoranda) + goods_id_info
                if error_tag:
                    continue
                export_goods_fields = ["goods_name", "goods_id", "quantity"]
                for i in range(len(export_goods_details)):
                    setattr(order, export_goods_fields[i], export_goods_details[i])
                order_fields = ["shop", "nickname", "receiver", "address", "mobile", "province", "city", "district", "erp_order_id", "warehouse"]

                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))
                if not order.warehouse:
                    order.warehouse = warehouse
                    obj.warehouse = warehouse
                order.ori_order = obj
                if obj.assign_express:
                    express = express_list.get(obj.assign_express, None)
                    if express:
                        order.cs_memoranda = "%s 指定%s" % (order.cs_memoranda, express)
                try:
                    order.buyer_remark = "%s%s" % (order.buyer_remark, obj.memo)
                    order.creator = request.user.username
                    order.save()
                    logging(order, user, LogManualOrderExport, "创建")
                except Exception as e:
                    data["error"].append("%s输出单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogManualOrder, "递交发货")
                all_goods_details.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        user = request.user
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
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogManualOrder, "驳回到提交")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=3)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_tag(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=0)
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
            else:
                report_dic["error"].append("%s UT无此货品" % row["goods_id"])
                report_dic["false"] += 1
                continue
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic


class TrialOrderTrackViewset(viewsets.ModelViewSet):
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
    serializer_class = ManualOrderSerializer
    filter_class = ManualOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return ManualOrder.objects.none()
        department = self.request.user.department
        queryset = ManualOrder.objects.filter(order_status__in=[2, 3], order_category=4).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["department"] = user.department
        params["order_status__in"] = '2, 3'
        params["order_category"] = 4
        f = ManualOrderFilter(params)
        serializer = ManualOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status__in"] = '2, 3'
        department = self.request.user.department
        params["department"] = department
        params["order_category"] = 4
        if all_select_tag:
            handle_list = ManualOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ManualOrder.objects.filter(id__in=order_ids, order_status__in=[2, 3], department=department)
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
        user = request.user
        if n:
            for obj in check_list:
                pass
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class TrialOrderManageViewset(viewsets.ModelViewSet):
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
    serializer_class = ManualOrderSerializer
    filter_class = ManualOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return ManualOrder.objects.none()
        queryset = ManualOrder.objects.filter(order_category=4).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_category"] = 4
        f = ManualOrderFilter(params)
        serializer = ManualOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = ManualOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogManualOrder)
        return Response(ret)

    @action(methods=['patch'], detail=False)
    def get_file_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = ManualOrder.objects.filter(id=id)[0]
        file_details = instance.mofiles_set.all()
        ret = []
        for file_detail in file_details:
            if file_detail.suffix in ['png', 'jpg', 'gif', 'bmp', 'tif', 'svg', 'raw']:
                is_pic = True
            else:
                is_pic = False
            data = {
                "id": file_detail.id,
                "name": file_detail.name,
                "suffix": file_detail.suffix,
                "url": file_detail.url,
                "url_list": [file_detail.url],
                "is_pic": is_pic
            }
            ret.append(data)
        return Response(ret)


class TOGoodsTrackViewset(viewsets.ModelViewSet):
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
    serializer_class = MOGoodsSerializer
    filter_class = MOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_mogoods']
    }

    def get_queryset(self):
        if not self.request:
            return MOGoods.objects.none()
        queryset = MOGoods.objects.filter(order_status__in=[2, 3, 4], settle_category=4).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status__in"] = "2, 3, 4"
        params["settle_category"] = 4

        f = MOGoodsFilter(params)
        serializer = MOGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status__in"] = "2, 3, 4"
        params["settle_category"] = 4
        if all_select_tag:
            handle_list = MOGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MOGoods.objects.filter(id__in=order_ids, order_status__in=[2, 3, 4], settle_category=4)
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
        user = request.user
        if n:
            for obj in check_list:
                pass
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


class TOGoodsManage(viewsets.ModelViewSet):
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
    serializer_class = MOGoodsSerializer
    filter_class = MOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_mogoods']
    }

    def get_queryset(self):
        if not self.request:
            return MOGoods.objects.none()
        queryset = MOGoods.objects.filter(settle_category=4).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["settle_category"] = 4
        f = MOGoodsFilter(params)
        serializer = MOGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)

        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = MOGoods.objects.filter(id=id)[0]
        ret = getlogs(instance, LogMOGoods)
        return Response(ret)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["settle_category"] = 4
        if all_select_tag:
            handle_list = MOGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MOGoods.objects.filter(id__in=order_ids, settle_category=4)
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
        user = request.user
        if n:
            for obj in check_list:
                pass
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def create_refund(self, request, *args, **kwargs):
        user = request.user
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
                if obj.order_status < 3:
                    data["error"].append("%s 未发货完成的单据不可创建退货单" % obj.id)
                    n -= 1
                    continue
                _q_repeat_refund = RefundTrialOrder.objects.filter(ori_order=obj)
                if _q_repeat_refund.exists():
                    if obj.sign != 1:
                        data["error"].append("%s 已存在退货单，重复创建需要设置特殊标记" % obj.id)
                        n -= 1
                        continue
                code = f"RE{str(obj.manual_order.erp_order_id)[-10:]}"
                refund_order_dict = {
                    "ori_order": obj,
                    "shop": obj.manual_order.shop,
                    "warehouse": obj.manual_order.warehouse,
                    "code": code,
                    "order_category": 1,
                    "sender": obj.manual_order.receiver,
                    "mobile": obj.manual_order.mobile,
                    "city": obj.manual_order.city,
                    "district": obj.manual_order.district,
                    "address": obj.manual_order.address,
                    "ori_amount": obj.amount,
                    "creator": user.username,
                }
                try:
                    refund_order = RefundTrialOrder.objects.create(**refund_order_dict)
                    refund_order.code = f"{refund_order.code}{refund_order.id}"
                    refund_order.save()
                    logging(refund_order, user, LogRefundTrialOrder, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id}退货单创建出错：{e}")
                    n -= 1
                    continue
                _q_repeat_refund_goods = RTOGoods.objects.filter(order=refund_order, goods=obj.goods_name, warehouse=obj.manual_order.warehouse)
                if _q_repeat_refund_goods.exists():
                    data["error"].append("%s 退货单已创建过此货品不可重复创建" % obj.id)
                    n -= 1
                    continue
                refund_order_goods_dict = {
                    "order": refund_order,
                    "code": f"{refund_order.code}{obj.goods_name.goods_id}",
                    "warehouse": obj.manual_order.warehouse,
                    "goods": obj.goods_name,
                    "quantity": obj.quantity,
                    "settlement_price": obj.price,
                    "settlement_amount": obj.price * obj.quantity,
                    "logistics_name": obj.logistics_name,
                    "logistics_no": obj.logistics_no,
                    "sub_trade_no": obj.sub_trade_no,
                    "invoice_id": obj.invoice_id,
                    "sn": obj.manual_order.m_sn,
                    "creator": user.username,
                }
                try:
                    refund_order_goods = RTOGoods.objects.create(**refund_order_goods_dict)
                    logging(refund_order_goods, user, LogRTOGoods, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id}退货单货品创建出错：{e}")
                    n -= 1
                    continue
                obj.is_delete = True
                obj.sign = 0
                obj.save()
                logging(obj, user, LogMOGoods, f"创建退货单{refund_order_goods.code}")
                obj.manual_order.is_delete = True
                obj.manual_order.save()
                logging(obj.manual_order, user, LogManualOrder, f"存在退货单{refund_order_goods.code}")

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in set_list:
                obj.sign = 1
                obj.save()
                logging(obj, user, LogMOGoods, "设置特殊标记，以通过重复创建退货单")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(set_list) - n
        return Response(data)


class RefundTrialOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundTrialOrderSerializer
    filter_class = RefundTrialOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return RefundTrialOrder.objects.none()
        queryset = RefundTrialOrder.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = RefundTrialOrderFilter(params)
        serializer = RefundTrialOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = RefundTrialOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = RefundTrialOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def create_logistic_order(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        create_list = self.get_handle_list(params)
        n = len(create_list)
        result_data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in create_list:
                if obj.process_tag != 0:
                    result_data["error"].append("%s 单据状态错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                if obj.return_type not in [3]:
                    result_data["error"].append("%s 取回方式非逆向取件" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if not re.match(r"^1[23456789]\d{9}$", obj.mobile):
                    result_data["error"].append("%s 退货人手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue
                _q_sender_customer = Customer.objects.filter(name=obj.mobile)
                if _q_sender_customer.exists():
                    sender_customer = _q_sender_customer[0]
                else:
                    sender_customer = Customer.objects.create(**{"name": str(obj.mobile)})
                    logging(sender_customer, user, LogCustomer, "退货时创建")

                _q_sender = CSAddress.objects.filter(customer=sender_customer, city=obj.city, name=obj.sender, mobile=obj.mobile, address=obj.address)
                if _q_sender.exists():
                    sender = _q_sender[0]
                else:
                    sender = CSAddress.objects.create(**{
                        "customer": sender_customer,
                        "city": obj.city,
                        "district": obj.district,
                        "name": obj.sender,
                        "mobile": obj.mobile,
                        "address": obj.address,
                        "memo": "退货时创建"
                    })
                    logging(sender, user, LogCSAddress, "退货时创建")

                if not re.match(r"^1[23456789]\d{9}$", obj.warehouse.mobile):
                    result_data["error"].append("%s 收货仓库手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                if not all((obj.warehouse.city, obj.warehouse.receiver, obj.warehouse.address,)):
                    result_data["error"].append("%s 收货仓库收货信息缺失" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                _q_receiver_customer = Customer.objects.filter(name=obj.warehouse.mobile)
                if _q_receiver_customer.exists():
                    receiver_customer = _q_receiver_customer[0]
                else:
                    receiver_customer = Customer.objects.create(**{"name": str(obj.warehouse.mobile)})
                    logging(receiver_customer, user, LogCustomer, "退货时创建收货仓库")

                _q_receiver = CSAddress.objects.filter(customer=receiver_customer, city=obj.warehouse.city, name=obj.warehouse.receiver, mobile=obj.warehouse.mobile, address=obj.warehouse.address)
                if _q_receiver.exists():
                    receiver = _q_receiver[0]
                else:
                    receiver = CSAddress.objects.create(**{
                        "customer": receiver_customer,
                        "city": obj.warehouse.city,
                        "district": obj.warehouse.district,
                        "name": obj.warehouse.receiver,
                        "mobile": obj.warehouse.mobile,
                        "address": obj.warehouse.address,
                        "memo": "退货时创建"
                    })
                    logging(receiver, user, LogCSAddress, "退货时创建")

                goods_details = obj.rtogoods_set.all()

                total_weight = goods_details.aggregate(total_weight=Sum(F("goods__weight") * F("quantity")))

                if total_weight["total_weight"] == 0:
                    result_data["error"].append("%s UT货品未设置重量" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                if len(goods_details) == 1:
                    goods_name = goods_details[0].goods.name
                else:
                    goods_name = reduce(lambda x, y: x + y, map(lambda x: f"{x.goods.name};", goods_details))
                data = {
                    "code": obj.code,
                    "warehouse": obj.warehouse,
                    "express": obj.express,
                    "sender": sender,
                    "receiver": receiver,
                    "weight": total_weight["total_weight"],
                    "goods_name": goods_name
                }

                # all_weight = [v for k, v in result.items()]
                return_data = CreateLogisticOrder(request, data=data)
                if return_data["false"]:
                    n -= 1
                    for error in return_data["error"]:
                        result_data["error"].append(error)
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                obj.process_tag =1
                obj.save()
                logging(obj, user, LogRefundTrialOrder, "确认物流单")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        result_data["successful"] = n
        result_data["false"] = len(create_list) - n
        return Response(result_data)

    @action(methods=['patch'], detail=False)
    def create_express_order(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        push_list = self.get_handle_list(params)
        n = len(push_list)
        result_data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in push_list:
                if obj.process_tag != 1:
                    result_data["error"].append("%s 非确认物流状态不可获取单号" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                _q_logistics_order = Logistics.objects.filter(code=obj.code)
                if _q_logistics_order.exists():
                    logistics_order = _q_logistics_order[0]
                    if logistics_order.order_status not in [0, 1]:
                        result_data["error"].append("%s 物流单单据状态错误" % obj.id)
                        n -= 1
                        obj.mistake_tag = 8
                        obj.save()
                        continue

                express_model = logistics_order.get_model_logistic()
                if express_model["model"] is None:
                    result_data["error"].append("%s 不支持此物流对接" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                _q_express_order = express_model["model"].objects.filter(order=logistics_order)
                if _q_express_order.exists():
                    express_order = _q_express_order[0]
                else:
                    result_data["error"].append("%s 物流单对应快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue

                result = express_order.createOrder(request)

                if not result["result"]:
                    n -= 1
                    for error in result["error"]:
                        result_data["error"].append(error)
                        obj.info_refund = f"{error}"
                        if error == '渠道单号或运单号重复！':
                            obj.info_refund = f"{obj.info_refund}需要操作更新快递单之后进行获取"
                            obj.mistake_tag = 11
                            obj.process_tag = 3
                            obj.save()
                            continue
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                else:
                    obj.track_no = result["track_no"]
                    obj.rtogoods_set.all().update(track_no=result["track_no"])

                obj.process_tag = 2
                obj.save()
                logging(obj, user, LogRefundTrialOrder, f"获取物流单号{obj.track_no}")
        else:
            raise serializers.ValidationError("没有可推送的单据！")
        result_data["successful"] = n
        result_data["false"] = len(push_list) - n
        return Response(result_data)

    @action(methods=['patch'], detail=False)
    def update_express(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if n:
            for obj in check_list:
                if obj.process_tag != 3:
                    data["error"].append("%s 更新物流单必须为获取单号失败的单子" % obj.id)
                    n -= 1
                    obj.mistake_tag = 12
                    obj.save()
                    continue
                _q_logistics_order = Logistics.objects.filter(code=obj.code)
                if _q_logistics_order.exists():
                    logistics_order = _q_logistics_order[0]
                    if logistics_order.order_status != 0:
                        data["error"].append("%s 对应物流单状态必须为取消" % obj.id)
                        n -= 1
                        obj.mistake_tag = 8
                        obj.save()
                        continue
                    else:
                        logistics_order.order_status = 1
                        logistics_order.save()

                express_model = logistics_order.get_model_logistic()
                if express_model["model"] is None:
                    data["error"].append("%s 不支持此物流对接" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                _q_express_order = express_model["model"].objects.filter(order=logistics_order)
                if _q_express_order.exists():
                    express_order = _q_express_order[0]
                    if express_order.order_status not in [1, 7, 8]:
                        data["error"].append("%s 快递详情单状态必须是{揽货失败，已撤销，已退回}状态时才可更新" % obj.id)
                        n -= 1
                        obj.mistake_tag = 14
                        obj.save()
                        continue
                else:
                    data["error"].append("%s 物流单对应快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                try:
                    express_order.transferCode(request)

                except Exception as e:
                    data["error"].append("%s 更新快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 15
                    obj.save()
                    continue
                obj.process_tag = 1
                obj.info_refund = ''
                obj.save()
                logging(obj, user, LogRefundTrialOrder, "更新快递详情单")

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def query_express(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if n:
            for obj in check_list:
                _q_logistics_order = Logistics.objects.filter(code=obj.code)
                if _q_logistics_order.exists():
                    logistics_order = _q_logistics_order[0]
                express_model = logistics_order.get_model_logistic()
                if express_model["model"] is None:
                    data["error"].append("%s 不支持此物流对接" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                _q_express_order = express_model["model"].objects.filter(order=logistics_order)
                if _q_express_order.exists():
                    express_order = _q_express_order[0]
                else:
                    data["error"].append("%s 物流单对应快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                try:
                    result = express_order.queryOrder(request)
                    if result["result"]:
                        obj.info_refund = result["statusType"]
                        if not obj.track_no:
                            obj.track_no = result["track_no"]
                        obj.save()
                        logging(obj, user, LogRefundTrialOrder, "查询快递详情单状态成功")
                    else:
                        data["error"].append("%s 查询快递详情失败" % obj.id)
                        n -= 1
                        obj.mistake_tag = 16
                        for error in result["error"]:
                            data["error"].append(error)
                            obj.info_refund = f"{error}"
                        obj.save()
                        continue
                except Exception as e:
                    data["error"].append(f"{obj.id}查询快递详情失败{e}")
                    n -= 1
                    obj.mistake_tag = 16
                    obj.save()
                    continue

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def cancel_express(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if n:
            for obj in check_list:
                _q_logistics_order = Logistics.objects.filter(code=obj.code)
                if _q_logistics_order.exists():
                    logistics_order = _q_logistics_order[0]
                express_model = logistics_order.get_model_logistic()
                if express_model["model"] is None:
                    data["error"].append("%s 不支持此物流对接" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                _q_express_order = express_model["model"].objects.filter(order=logistics_order)
                if _q_express_order.exists():
                    express_order = _q_express_order[0]
                else:
                    data["error"].append("%s 物流单对应快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                try:
                    result = express_order.cancelOrder(request)
                    if result["result"]:
                        obj.info_refund = "快递单撤销成功"
                        obj.track_no = ''
                        obj.save()
                        logging(obj, user, LogRefundTrialOrder, "撤销快递详情单状态成功")
                    else:
                        data["error"].append("%s 撤销快递详情失败" % obj.id)
                        n -= 1
                        obj.mistake_tag = 17
                        for error in result["error"]:
                            data["error"].append(error)
                            obj.info_refund = f"{error}"
                        obj.save()
                        continue
                except Exception as e:
                    data["error"].append(f"{obj.id}查询快递详情失败{e}")
                    n -= 1
                    obj.mistake_tag = 16
                    obj.save()
                    continue

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
        user = request.user
        warehouse = Warehouse.objects.filter(name="北京体验仓")[0]
        if n:
            for obj in check_list:
                if not obj.erp_order_id:
                    _prefix = "SSTO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = _prefix + serial_number + str(obj.id)
                    obj.save()
                if not obj.warehouse:
                    obj.warehouse = warehouse
                    obj.save()
                    if "体验" in str(obj.warehouse.name):
                        data["error"].append("%s 仓库非体验仓无法提交" % obj.id)
                        n -= 1
                        obj.mistake_tag = 18
                        obj.save()
                        continue
                all_goods_details = obj.mogoods_set.all()
                if not all_goods_details.exists():
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 15
                    obj.save()
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status > 1:
                        data["error"].append("%s 关联出库单错误，联系管理员" % obj.id)
                        n -= 1
                        obj.mistake_tag = 16
                        obj.save()
                        continue
                    else:
                        outbound.order_status = 1
                else:
                    outbound = Outbound()
                    suffix = str(datetime.datetime.now().date()).replace("-", "")
                    outbound.code = f"ODO{suffix}"
                outbound.warehouse = obj.warehouse
                outbound.verification = obj.erp_order_id

                try:
                    outbound.creator = user.username
                    outbound.save()
                    outbound.code = f'{outbound.code}-{outbound.id}'
                    outbound.save()
                    logging(outbound, user, LogOutbound, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id} 关联出库单创建错误：{e}")
                    n -= 1
                    obj.mistake_tag = 17
                    obj.save()
                    continue
                outbound.outbounddetail_set.all().delete()
                for goods in all_goods_details:
                    outbound_goods_dict = {
                        "order": outbound,
                        "goods": goods.goods_name,
                        "code": outbound.code,
                        "category": 1,
                        "warehouse": obj.warehouse,
                        "quantity": goods.quantity,
                        "price": goods.price,
                        "memo": goods.memorandum,
                    }
                    outbound_goods = OutboundDetail.objects.create(**outbound_goods_dict)
                    outbound_goods.code = f'{outbound_goods.code}-{outbound_goods.id}'
                    outbound_goods.save()
                    logging(outbound_goods, user, LogOutboundDetail, "创建")
                obj.process_tag = 1
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogManualOrder, "递交试用申请")
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_tag(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=0)
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
            else:
                report_dic["error"].append("%s UT无此货品" % row["goods_id"])
                report_dic["false"] += 1
                continue
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = ManualOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/sales/trialgoods"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = MOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = user.username
                photo_order.save()
                logging(work_order, user, LogManualOrder, f"上传图片{photo_order.name}")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class RefundTrialOrderCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundTrialOrderSerializer
    filter_class = RefundTrialOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return RefundTrialOrder.objects.none()
        queryset = RefundTrialOrder.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = RefundTrialOrderFilter(params)
        serializer = RefundTrialOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = RefundTrialOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = RefundTrialOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def cancel_express(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if n:
            for obj in check_list:
                _q_logistics_order = Logistics.objects.filter(code=obj.code)
                if _q_logistics_order.exists():
                    logistics_order = _q_logistics_order[0]
                express_model = logistics_order.get_model_logistic()
                if express_model["model"] is None:
                    data["error"].append("%s 不支持此物流对接" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                _q_express_order = express_model["model"].objects.filter(order=logistics_order)
                if _q_express_order.exists():
                    express_order = _q_express_order[0]
                else:
                    data["error"].append("%s 物流单对应快递详情单错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                try:
                    result = express_order.cancelOrder(request)
                    if result["result"]:
                        obj.info_refund = "快递单撤销成功"
                        obj.track_no = ''
                        obj.save()
                        logging(obj, user, LogRefundTrialOrder, "撤销快递详情单状态成功")
                    else:
                        data["error"].append("%s 撤销快递详情失败" % obj.id)
                        n -= 1
                        obj.mistake_tag = 17
                        for error in result["error"]:
                            data["error"].append(error)
                            obj.info_refund = f"{error}"
                        obj.save()
                        continue
                except Exception as e:
                    data["error"].append(f"{obj.id}查询快递详情失败{e}")
                    n -= 1
                    obj.mistake_tag = 16
                    obj.save()
                    continue

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
        user = request.user
        warehouse = Warehouse.objects.filter(name="北京体验仓")[0]
        if n:
            for obj in check_list:
                if not obj.erp_order_id:
                    _prefix = "SSTO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = _prefix + serial_number + str(obj.id)
                    obj.save()
                if not obj.warehouse:
                    obj.warehouse = warehouse
                    obj.save()
                    if "体验" in str(obj.warehouse.name):
                        data["error"].append("%s 仓库非体验仓无法提交" % obj.id)
                        n -= 1
                        obj.mistake_tag = 18
                        obj.save()
                        continue
                all_goods_details = obj.mogoods_set.all()
                if not all_goods_details.exists():
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 15
                    obj.save()
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.erp_order_id)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status > 1:
                        data["error"].append("%s 关联出库单错误，联系管理员" % obj.id)
                        n -= 1
                        obj.mistake_tag = 16
                        obj.save()
                        continue
                    else:
                        outbound.order_status = 1
                else:
                    outbound = Outbound()
                    suffix = str(datetime.datetime.now().date()).replace("-", "")
                    outbound.code = f"ODO{suffix}"
                outbound.warehouse = obj.warehouse
                outbound.verification = obj.erp_order_id

                try:
                    outbound.creator = user.username
                    outbound.save()
                    outbound.code = f'{outbound.code}-{outbound.id}'
                    outbound.save()
                    logging(outbound, user, LogOutbound, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id} 关联出库单创建错误：{e}")
                    n -= 1
                    obj.mistake_tag = 17
                    obj.save()
                    continue
                outbound.outbounddetail_set.all().delete()
                for goods in all_goods_details:
                    outbound_goods_dict = {
                        "order": outbound,
                        "goods": goods.goods_name,
                        "code": outbound.code,
                        "category": 1,
                        "warehouse": obj.warehouse,
                        "quantity": goods.quantity,
                        "price": goods.price,
                        "memo": goods.memorandum,
                    }
                    outbound_goods = OutboundDetail.objects.create(**outbound_goods_dict)
                    outbound_goods.code = f'{outbound_goods.code}-{outbound_goods.id}'
                    outbound_goods.save()
                    logging(outbound_goods, user, LogOutboundDetail, "创建")
                obj.process_tag = 1
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogManualOrder, "递交试用申请")
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_tag(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=0)
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
            else:
                report_dic["error"].append("%s UT无此货品" % row["goods_id"])
                report_dic["false"] += 1
                continue
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = ManualOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/sales/trialgoods"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = MOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = user.username
                photo_order.save()
                logging(work_order, user, LogManualOrder, f"上传图片{photo_order.name}")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class RefundTrialOrderManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundTrialOrderSerializer
    filter_class = RefundTrialOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return RefundTrialOrder.objects.none()
        queryset = RefundTrialOrder.objects.filter(order_category=4).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_category"] = 4
        f = RefundTrialOrderFilter(params)
        serializer = RefundTrialOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = RefundTrialOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRefundTrialOrder)
        return Response(ret)





