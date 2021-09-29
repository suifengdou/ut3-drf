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
from .models import OriCallLog, CallLog
from .serializers import OriCallLogSerializer, CallLogSerializer
from .filters import OriCallLogFilter, CallLogFilter
from apps.utils.geography.models import Province, City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.utils.geography.tools import PickOutAdress


class OriCallLogSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriCallLogSerializer
    filter_class = OriCallLogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['callcenter.view_oricalllog',]
    }

    def get_queryset(self):
        if not self.request:
            return OriCallLog.objects.none()
        queryset = OriCallLog.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriCallLogFilter(params)
        serializer = OriCallLogSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriCallLogFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriCallLog.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        category_list = {
            "质量问题": 1,
            "开箱即损": 2,
            "礼品赠品": 3,
        }
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        if n:
            for obj in check_list:
                if obj.erp_order_id:
                    _q_repeat_order = ManualOrder.objects.filter(erp_order_id=obj.erp_order_id)
                    if _q_repeat_order.exists():
                        order = _q_repeat_order[0]
                        if order.order_status in [0, 1]:
                            order.order_status = 1
                        else:
                            data["error"].append("%s 重复递交，已存在输出单据" % obj.id)
                            n -= 1
                            obj.mistake_tag = 1
                            obj.save()
                            continue
                    else:
                        order = ManualOrder()
                        order.erp_order_id = obj.erp_order_id
                else:
                    order =  ManualOrder()
                    _prefix = "CO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                    order.erp_order_id = obj.erp_order_id
                    obj.save()
                order.order_category = category_list.get(obj.order_category, None)
                order.nickname = obj.receiver
                order_fields = ["receiver", "m_sn", "broken_part", "description"]
                for key_word in order_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                if not order.order_category:
                    data["error"].append("%s 无补寄原因" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue
                if order.order_category != 3 and not any((obj.broken_part, obj.m_sn, obj.description)):
                    data["error"].append("%s 非赠品必须所有损害部位，sn和描述" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop)
                if not _q_shop.exists():
                    data["error"].append("%s 无店铺" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                else:
                    order.shop = _q_shop[0]
                if not re.match(r"^1[3456789]\d{9}$", obj.mobile):
                    data["error"].append("%s 手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                else:
                    order.mobile = obj.mobile

                order.address = str(obj.area) + str(obj.address)
                address = re.sub("[0-9!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", order.address)
                seg_list = jieba.lcut(address)

                _spilt_addr = PickOutAdress(seg_list)
                _rt_addr = _spilt_addr.pickout_addr()
                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                if not order.city:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue

                if order.province != order.city.province:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                if address.find(str(order.province.name)[:2]) == -1 and address.find(str(order.city.name)[:2]) == -1:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                if order.city.name not in special_city and not order.district:
                    order.district = District.objects.filter(city=order.city, name="其他区")[0]

                if '集运' in str(obj.address):
                    data["error"].append("%s地址是集运仓" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue



                try:
                    order.department = request.user.department
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data["error"].append("%s输出单保存出错: %s" % obj.id)
                    n -= 1
                    obj.mistake_tag = 8
                    obj.save()
                    continue

                goods_details = str(obj.goods_details).split("+")
                goods_list = []

                if len(goods_details) == 1:
                    if "*" in obj.goods_details:
                        goods_details = obj.goods_details.split("*")
                        goods_name = re.sub("(整机：)|(整机:)", "", str(goods_details[0]).strip())
                        _q_goods = Goods.objects.filter(name=goods_name)
                        if _q_goods.exists():
                            goods_list.append([_q_goods[0], str(goods_details[1]).strip()])
                        else:
                            data["error"].append("%s 货品错误" % obj.id)
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
                            continue
                    else:
                        data["error"].append("%s 货品错误（无乘号）" % obj.id)
                        n -= 1
                        obj.mistake_tag = 9
                        obj.save()
                        continue
                elif len(goods_details) > 1:
                    error_tag = 0
                    goods_details = list(map(lambda x: x.split("*"), goods_details))
                    goods_names = set(list(map(lambda x: x[0], goods_details)))
                    if len(goods_names) != len(goods_details):
                        data["error"].append("%s 明细中货品重复" % obj.id)
                        n -= 1
                        obj.mistake_tag = 10
                        obj.save()
                        continue
                    for goods in goods_details:
                        if len(goods) == 2:
                            goods_name = re.sub("(整机：)|(整机:)", "", str(goods[0]).strip())
                            _q_goods = Goods.objects.filter(name=goods_name)
                            if _q_goods.exists():
                                goods_list.append([_q_goods[0], str(goods[1]).strip()])
                            else:
                                data["error"].append("%s 货品错误" % obj.id)
                                error_tag = 1
                                n -= 1
                                obj.mistake_tag = 9
                                obj.save()
                                break
                        else:
                            data["error"].append("%s 货品错误" % obj.id)
                            error_tag = 1
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
                            break
                    if error_tag:
                        continue
                else:
                    data["error"].append("%s 货品错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 9
                    obj.save()
                    continue

                for goods_info in goods_list:
                    order_detail = MOGoods()
                    order_detail.goods_name = goods_info[0]
                    order_detail.quantity = goods_info[1]
                    order_detail.goods_id = goods_info[0].goods_id
                    try:
                        order_detail.manual_order = order
                        order_detail.creator = request.user.username
                        order_detail.save()
                    except Exception as e:
                        data["error"].append("%s 输出单保存出错" % obj.id)
                        n -= 1
                        obj.mistake_tag = 11
                        obj.save()
                        continue
                obj.order_status = 3
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
        print(request)
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
            "通话ID": "call_id",
            "类型": "category",
            "开启服务时间": "start_time",
            "结束服务时间": "end_time",
            "服务时长": "total_duration",
            "通话时长": "call_duration",
            "排队时长": "queue_time",
            "振铃时长": "ring_time",
            "静音时长": "muted_duration",
            "静音次数": "muted_time",
            "主叫号码": "calling_num",
            "被叫号码": "called_num",
            "号码归属地": "attribution",
            "用户名": "nickname",
            "手机号码": "smartphone",
            "ivr语音导航": "ivr",
            "分流客服组": "group",
            "接待客服": "servicer",
            "重复咨询": "repeated_num",
            "接听状态": "answer_status",
            "挂机方": "on_hook",
            "满意度": "satisfaction",
            "服务录音": "call_recording",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "咨询备注": "remark",
            "问题解决状态": "problem_status",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "产品型号": "goods_type",
            "出厂序列号": "m_sn",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "收件人姓名": "receiver",
            "建单手机": "mobile",
            "省市区": "area",
            "详细地址": "address"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["通话ID", "类型", "开启服务时间", "结束服务时间", "服务时长", "通话时长", "排队时长",
                             "振铃时长", "静音时长", "静音次数", "主叫号码", "被叫号码", "号码归属地", "用户名",
                             "手机号码", "ivr语音导航", "分流客服组", "接待客服", "重复咨询", "接听状态", "挂机方",
                             "满意度", "服务录音", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "咨询备注", "问题解决状态", "购买日期", "购买店铺", "产品型号", "出厂序列号",
                             "补寄原因", "配件信息", "损坏部位", "损坏描述", "收件人姓名",
                             "建单手机", "省市区", "详细地址"]

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
            _ret_verify_field = OriCallLog.verify_mandatory(columns_key)
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
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            _q_calllog = OriCallLog.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = OriCallLog()
            order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                            "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                            "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                            "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                            "call_recording", "primary_classification", "secondary_classification",
                            "three_level_classification", "four_level_classification", "five_level_classification",
                            "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn",
                            "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                            "area", "address"]
            if len(str(row["remark"])) > 349:
                row["remark"] = row["remark"][:349]
            for field in order_fields:
                if str(row[field]) == "nan":
                    row[field] = ""
                setattr(order, field, row[field])
            if all((order.receiver, order.mobile, order.address)):
                order.is_order = True
            else:
                order.order_status =2
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1

        return report_dic


class OriCallLogCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = OriCallLogSerializer
    filter_class = OriCallLogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['callcenter.view_oricalllog']
    }

    def get_queryset(self):
        if not self.request:
            return OriCallLog.objects.none()
        queryset = OriCallLog.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = OriCallLogFilter(params)
        serializer = OriCallLogSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriCallLogFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriCallLog.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
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
                order = CallLog()
                order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                                "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                                "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                                "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                                "call_recording", "primary_classification", "secondary_classification",
                                "three_level_classification", "four_level_classification", "five_level_classification",
                                "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn",
                                "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                                "area", "address"]

                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))
                _q_goods_name = MOGoods.objects.filter(manual_order=order, goods_name=obj.goods_name)
                if _q_goods_name.exists():
                    data["error"].append("%s重复递交，已存在输出单据" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
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
        print(request)
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
            "通话ID": "call_id",
            "类型": "category",
            "开启服务时间": "start_time",
            "结束服务时间": "end_time",
            "服务时长": "total_duration",
            "通话时长": "call_duration",
            "排队时长": "queue_time",
            "振铃时长": "ring_time",
            "静音时长": "muted_duration",
            "静音次数": "muted_time",
            "主叫号码": "calling_num",
            "被叫号码": "called_num",
            "号码归属地": "attribution",
            "用户名": "nickname",
            "手机号码": "smartphone",
            "ivr语音导航": "ivr",
            "分流客服组": "group",
            "接待客服": "servicer",
            "重复咨询": "repeated_num",
            "接听状态": "answer_status",
            "挂机方": "on_hook",
            "满意度": "satisfaction",
            "服务录音": "call_recording",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "咨询备注": "remark",
            "问题解决状态": "problem_status",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "产品型号": "goods_type",
            "出厂序列号": "m_sn",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "收件人姓名": "receiver",
            "建单手机": "mobile",
            "省市区": "area",
            "详细地址": "address"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["通话ID", "类型", "开启服务时间", "结束服务时间", "服务时长", "通话时长", "排队时长",
                             "振铃时长", "静音时长", "静音次数", "主叫号码", "被叫号码", "号码归属地", "用户名",
                             "手机号码", "ivr语音导航", "分流客服组", "接待客服", "重复咨询", "接听状态", "挂机方",
                             "满意度", "服务录音", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "咨询备注", "问题解决状态", "购买日期", "购买店铺", "产品型号", "出厂序列号",
                             "补寄原因", "配件信息", "损坏部位", "损坏描述", "收件人姓名",
                             "建单手机", "省市区", "详细地址"]

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
            _ret_verify_field = OriCallLog.verify_mandatory(columns_key)
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
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            _q_calllog = OriCallLog.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = OriCallLog()
            order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                            "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                            "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                            "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                            "call_recording", "primary_classification", "secondary_classification",
                            "three_level_classification", "four_level_classification", "five_level_classification",
                            "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn",
                            "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                            "area", "address"]
            if len(str(row["remark"])) > 349:
                row["remark"] = row["remark"][:349]
            for field in order_fields:
                if str(row[field]) == "nan":
                    row[field] = ""
                setattr(order, field, row[field])
            if all((order.receiver, order.mobile, order.area, order.address)):
                order.is_order = True
            else:
                order.order_status =2
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1

        return report_dic


class OriCallLogViewset(viewsets.ModelViewSet):
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
    serializer_class = OriCallLogSerializer
    filter_class = OriCallLogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['callcenter.view_oricalllog']
    }

    def get_queryset(self):
        if not self.request:
            return OriCallLog.objects.none()
        queryset = OriCallLog.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriCallLogFilter(params)
        serializer = OriCallLogSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriCallLogFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriCallLog.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
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
                address = re.sub("[0-9!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(obj.address))
                seg_list = jieba.lcut(address)
                num = 0
                for words in seg_list:
                    num += 1
                    if not order.province:
                        _q_province = Province.objects.filter(name__contains=words)
                        if len(_q_province) == 1:
                            if not _q_province.exists():
                                _q_province_again = Province.objects.filter(name__contains=words[:2])
                                if _q_province_again.exists():
                                    order.province = _q_province_again[0]
                            else:
                                order.province = _q_province[0]
                    if not order.city:
                        _q_city = City.objects.filter(name__contains=words)
                        if len(_q_city) == 1:
                            if not _q_city.exists():
                                _q_city_again = City.objects.filter(name__contains=words[:2])
                                if _q_city_again.exists():
                                    order.city = _q_city_again[0]
                                    if num < 3 and not order.province:
                                        order.province = order.city.province
                            else:
                                order.city = _q_city[0]
                                if num < 3 and not order.province:
                                    order.province = order.city.province
                    if not order.district:
                        if not order.city:
                            _q_district_direct = District.objects.filter(province=order.province, name__contains=words)
                            if len(_q_district_direct) == 1:
                                if _q_district_direct.exists():
                                    order.district = _q_district_direct[0]
                                    order.city = order.district.city
                                    break
                        else:
                            if order.city.name in special_city:
                                break
                            _q_district = District.objects.filter(city=order.city, name__contains=words)
                            if not _q_district:
                                _q_district_again = District.objects.filter(province=order.province, name__contains=words)
                                if len(_q_district_again) == 1:
                                    if _q_district_again.exists():
                                        order.district = _q_district_again[0]
                                        order.city = order.district.city
                                        break
                            else:
                                order.district = _q_district[0]
                                break
                if not order.city:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue

                if order.province != order.city.province:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if address.find(str(order.province.name)[:2]) == -1 and address.find(str(order.city.name)[:2]) == -1:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if order.city.name not in special_city and not order.district:
                    order.district = District.objects.filter(city=order.city, name="其他区")[0]
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

                order_fields = ["shop", "nickname", "receiver", "address", "mobile", "erp_order_id", "order_id"]
                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))

                try:
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
        print(request)
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
            "通话ID": "call_id",
            "类型": "category",
            "开启服务时间": "start_time",
            "结束服务时间": "end_time",
            "服务时长": "total_duration",
            "通话时长": "call_duration",
            "排队时长": "queue_time",
            "振铃时长": "ring_time",
            "静音时长": "muted_duration",
            "静音次数": "muted_time",
            "主叫号码": "calling_num",
            "被叫号码": "called_num",
            "号码归属地": "attribution",
            "用户名": "nickname",
            "手机号码": "smartphone",
            "ivr语音导航": "ivr",
            "分流客服组": "group",
            "接待客服": "servicer",
            "重复咨询": "repeated_num",
            "接听状态": "answer_status",
            "挂机方": "on_hook",
            "满意度": "satisfaction",
            "服务录音": "call_recording",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "咨询备注": "remark",
            "问题解决状态": "problem_status",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "产品型号": "goods_type",
            "出厂序列号": "m_sn",
            "是否建配件工单": "is_order",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "收件人姓名": "receiver",
            "建单手机": "mobile",
            "省市区": "area",
            "详细地址": "address"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["通话ID", "类型", "开启服务时间", "结束服务时间", "服务时长", "通话时长", "排队时长",
                             "振铃时长", "静音时长", "静音次数", "主叫号码", "被叫号码", "号码归属地", "用户名",
                             "手机号码", "ivr语音导航", "分流客服组", "接待客服", "重复咨询", "接听状态", "挂机方",
                             "满意度", "服务录音", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "咨询备注", "问题解决状态", "购买日期", "购买店铺", "产品型号", "出厂序列号",
                             "是否建配件工单", "补寄原因", "配件信息", "损坏部位", "损坏描述", "收件人姓名",
                             "建单手机", "省市区", "详细地址"]

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
            _ret_verify_field = OriCallLog.verify_mandatory(columns_key)
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
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            _q_calllog = OriCallLog.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = OriCallLog()
            order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                            "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                            "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                            "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                            "call_recording", "primary_classification", "secondary_classification",
                            "three_level_classification", "four_level_classification", "five_level_classification",
                            "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn", "is_order",
                            "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                            "area", "address"]
            for field in order_fields:
                setattr(order, field, row[field])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1

        return report_dic


class CallLogViewset(viewsets.ModelViewSet):
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
    serializer_class = CallLogSerializer
    filter_class = CallLogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['callcenter.view_calllog']
    }

    def get_queryset(self):
        if not self.request:
            return CallLog.objects.none()
        queryset = CallLog.objects.filter(extract_tag=False, category__in=[1, 2]).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = CallLogFilter(params)
        serializer = CallLogSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CallLogFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CallLog.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
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
                address = re.sub("[0-9!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(obj.address))
                seg_list = jieba.lcut(address)
                num = 0
                for words in seg_list:
                    num += 1
                    if not order.province:
                        _q_province = Province.objects.filter(name__contains=words)
                        if len(_q_province) == 1:
                            if not _q_province.exists():
                                _q_province_again = Province.objects.filter(name__contains=words[:2])
                                if _q_province_again.exists():
                                    order.province = _q_province_again[0]
                            else:
                                order.province = _q_province[0]
                    if not order.city:
                        _q_city = City.objects.filter(name__contains=words)
                        if len(_q_city) == 1:
                            if not _q_city.exists():
                                _q_city_again = City.objects.filter(name__contains=words[:2])
                                if _q_city_again.exists():
                                    order.city = _q_city_again[0]
                                    if num < 3 and not order.province:
                                        order.province = order.city.province
                            else:
                                order.city = _q_city[0]
                                if num < 3 and not order.province:
                                    order.province = order.city.province
                    if not order.district:
                        if not order.city:
                            _q_district_direct = District.objects.filter(province=order.province, name__contains=words)
                            if len(_q_district_direct) == 1:
                                if _q_district_direct.exists():
                                    order.district = _q_district_direct[0]
                                    order.city = order.district.city
                                    break
                        else:
                            if order.city.name in special_city:
                                break
                            _q_district = District.objects.filter(city=order.city, name__contains=words)
                            if not _q_district:
                                _q_district_again = District.objects.filter(province=order.province, name__contains=words)
                                if len(_q_district_again) == 1:
                                    if _q_district_again.exists():
                                        order.district = _q_district_again[0]
                                        order.city = order.district.city
                                        break
                            else:
                                order.district = _q_district[0]
                                break
                if not order.city:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue

                if order.province != order.city.province:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if address.find(str(order.province.name)[:2]) == -1 and address.find(str(order.city.name)[:2]) == -1:
                    data["error"].append("%s 地址无法提取省市区" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if order.city.name not in special_city and not order.district:
                    order.district = District.objects.filter(city=order.city, name="其他区")[0]
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

                order_fields = ["shop", "nickname", "receiver", "address", "mobile", "erp_order_id", "order_id"]
                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))

                try:
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



