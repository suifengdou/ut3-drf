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
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import DealerParts, DPGoods
from .serializers import DealerPartsSerializer, DPGoodsSerializer
from .filters import DealerPartsFilter, DPGoodsFilter
from apps.utils.geography.models import City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from ut3.settings import EXPORT_TOPLIMIT


class DealerPartsCreateViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerPartsSerializer
    filter_class = DealerPartsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_user_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerParts.objects.none()
        user = self.request.user
        queryset = DealerParts.objects.filter(order_status=1, creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["creator"] = user.username
        params["order_status"] = 1
        f = DealerPartsFilter(params)
        serializer = DealerPartsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        user = self.request.user
        params["creator"] = user.username
        if all_select_tag:
            handle_list = DealerPartsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerParts.objects.filter(id__in=order_ids, order_status=1, creator=user.username)
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
                if not obj.erp_order_id:
                    _prefix = "TBDP"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                    obj.save()

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

                if '集运' in str(obj.address):
                    data["error"].append("%s地址是集运仓" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                goods_tag = 0
                all_goods_details = obj.dpgoods_set.all()
                if all_goods_details:
                    for goods_detail in all_goods_details:
                        if goods_detail.goods_name.goods_attribute == 1:
                            goods_tag = 1
                            break
                if goods_tag:
                    data["error"].append("%s此工单仅支持配件" % obj.id)
                    n -= 1
                    obj.mistake_tag = 12
                    obj.save()
                    continue
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
            for obj in reject_list:
                obj.dpgoods_set.all().delete()
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
            '订单编号': 'order_id',
            '收件人': 'receiver',
            '地址': 'address',
            '手机': 'mobile',
            '货品编码': 'goods_id',
            '数量': 'quantity',
            '单据类型': 'order_category',
            '问题信息': 'information',
            '机器序列号': 'm_sn',
            '故障部位': 'broken_part',
            '故障描述': 'description',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["店铺", "客户网名", "收件人", "订单编号", "地址", "手机", "货品编码", "货品名称", "数量", "单据类型",
                             "问题信息", "机器序列号", "故障部位", "故障描述"]

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
            _ret_verify_field = DealerParts.verify_mandatory(columns_key)
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

            order_fields = ["nickname", "receiver", "order_id", "address", "mobile", "information", "m_sn", "broken_part", "description"]
            if not row["order_id"]:
                report_dic["error"].append("%s 无订单编号" % row["receiver"])
                report_dic["false"] += 1
                continue
            _q_order_exists = DealerParts.objects.filter(order_id=row["order_id"])
            if _q_order_exists.exists():
                order = _q_order_exists[0]
                if order.order_status != 1:
                    report_dic["error"].append("%s 重复创建" % order.order_id)
                    report_dic["false"] += 1
                    continue
            else:
                order = DealerParts()
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
                order.department = request.user.department
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
            goods_details = DPGoods()
            goods_details.dealer_parts = order
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
                report_dic['error'].append("%s 保存明细出错" % row["order_id"])
        return report_dic


class DealerPartsSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerPartsSerializer
    filter_class = DealerPartsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_handler_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerParts.objects.none()
        user = self.request.user
        shop = Shop.objects.filter(name="小狗吸尘器抖音旗舰店")[0]
        if user.platform.name == '抖音':
            queryset = DealerParts.objects.filter(shop=shop, order_status=2).order_by("-id")
        else:
            queryset = DealerParts.objects.filter(order_status=2).exclude(shop=shop).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = DealerPartsFilter(params)
        serializer = DealerPartsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DealerPartsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerParts.objects.filter(id__in=order_ids, order_status=2)
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
                obj.order_status = 1
                obj.save()
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
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic


class DealerPartsManageViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerPartsSerializer
    filter_class = DealerPartsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealerparts.view_dealerparts',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerParts.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = DealerParts.objects.all().order_by("-id")
        else:
            queryset = DealerParts.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):

        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        user = request.user
        if user.is_our:
            params["creator"] = user.username
        f = DealerPartsFilter(params)
        serializer = DealerPartsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)





