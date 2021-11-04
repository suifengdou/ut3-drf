import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np
import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict
from functools import reduce

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
from .models import Servicer, DialogTB, DialogTBDetail, DialogTBWords, DialogJD, DialogJDDetail, DialogJDWords, \
    DialogOW, DialogOWDetail, DialogOWWords
from .serializers import ServicerSerializer, DialogTBSerializer, DialogTBDetailSerializer, DialogTBWordsSerializer, \
    DialogJDSerializer, DialogJDDetailSerializer, DialogJDWordsSerializer, DialogOWSerializer, DialogOWDetailSerializer, \
    DialogOWWordsSerializer
from .filters import ServicerFilter, DialogTBFilter, DialogTBDetailFilter, DialogTBWordsFilter, DialogJDFilter, \
    DialogJDDetailFilter, DialogJDWordsFilter, DialogOWFilter, DialogOWDetailFilter, DialogOWWordsFilter
from apps.utils.geography.models import Province, City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.dfc.compensation.models import Compensation
from apps.utils.geography.tools import PickOutAdress
from apps.auth.users.models import UserProfile


class ServicerViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品
    list:
        返回货品列表
    update:
        更新货品信息
    destroy:
        删除货品信息
    create:
        创建货品信息
    partial_update:
        更新部分货品字段
    """
    queryset = Servicer.objects.all().order_by("id")
    serializer_class = ServicerSerializer
    filter_class = ServicerFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_servicer']
    }


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
            filter_fields = ["店铺", "账号", "昵称", "客服类型"]
            INIT_FIELDS_DIC = {
                "店铺": "shop",
                "账号": "username",
                "昵称": "name",
                "客服类型": "category"
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
            _ret_verify_field = Servicer.verify_mandatory(result_columns)
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
        category_dic = {"人工": 1, "机器人": 0}
        for row in resource:
            _q_order = Servicer.objects.filter(name=row["name"])
            if _q_order.exists():
                order = _q_order[0]
            else:
                order = Servicer()
            _q_shop = Shop.objects.filter(name=row["shop"])
            if _q_shop.exists():
                order.shop = _q_shop[0]
            else:
                report_dic["error"].append("店铺名称错误")
                continue
            _q_username = UserProfile.objects.filter(username=row["username"])
            if _q_username.exists():
                order.username = _q_username[0]
            else:
                report_dic["error"].append("无此账号")
                continue
            order.category = category_dic.get(row["category"])
            order.name = row["name"]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
        return report_dic


class DialogTBViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogTBSerializer
    filter_class = DialogTBFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogtb']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTB.objects.none()
        queryset = DialogTB.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogTBFilter(params)
        serializer = DialogTBSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogTBFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogTB.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):

        ALLOWED_EXTENSIONS = ['txt']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            start_tag = 0

            dialog_contents = []
            dialog_content = []
            i = 0
            while True:
                i += 1
                try:
                    data_line = _file.readline().decode('gbk')
                except Exception as e:
                    continue

                if i == 1:
                    try:
                        info = str(data_line).strip().replace('\n', '').replace('\r', '')
                        if ":" in info:
                            info = info.split(":")[0]
                        shop = info
                        if not shop:
                            report_dic['error'].append('请使用源表进行导入，不要对表格进行处理。')
                            break
                        continue
                    except Exception as e:
                        report_dic['error'].append('请使用源表进行导入，不要对表格进行处理。')
                        break

                customer = re.findall(r'^-{28}(.*)-{28}', data_line)
                if customer:
                    if dialog_content:
                        dialog_contents.append(dialog_content)
                        dialog_content = []
                    if dialog_contents:
                        intermediate_report_dic = self.save_contents(request, shop, current_customer, dialog_contents)
                        for k, v in intermediate_report_dic.items():
                            if k == "error":
                                if intermediate_report_dic["error"]:
                                    report_dic[k].append(v)
                            else:
                                report_dic[k] += v
                        dialog_contents.clear()
                        dialog_content.clear()
                        current_customer = customer[0]
                    else:
                        current_customer = customer[0]
                    start_tag = 1
                    continue
                if start_tag:
                    dialog = re.findall(r'(.*)(\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\):  )(.*)', str(data_line))
                    if dialog:
                        if len(dialog[0]) == 3:
                            if dialog_content:
                                dialog_contents.append(dialog_content)
                                dialog_content = []
                            sayer = dialog[0][0]
                            sayer = re.sub("cntaobao", "", str(sayer))
                            dialog_content.append(sayer)
                            dialog_content.append(str(dialog[0][1]).replace('(', '').replace('):  ', ''))
                            dialog_content.append(str(dialog[0][2]))
                    else:
                        # 这一块需要重新调试看看是干啥呢
                        try:
                            dialog_content[2] = '%s%s' % (dialog_content[2], str(data_line))

                        except Exception as e:
                            report_dic['error'].append(e)

                if re.match(r'^={64}', str(data_line)):
                    if dialog_content:
                        dialog_contents.append(dialog_content)
                        dialog_content = []
                    if dialog_contents:
                        intermediate_report_dic = self.save_contents(request, shop, current_customer, dialog_contents)
                        for k, v in intermediate_report_dic.items():
                            if k == "error":
                                if intermediate_report_dic["error"]:
                                    report_dic[k].append(v)
                            else:
                                report_dic[k] += v
                        start_tag = 0
                if not data_line:
                    if dialog_content:
                        dialog_contents.append(dialog_content)
                    if dialog_contents:
                        intermediate_report_dic = self.save_contents(request, shop, current_customer, dialog_contents)
                        for k, v in intermediate_report_dic.items():
                            if k == "error":
                                if intermediate_report_dic["error"]:
                                    report_dic[k].append(v)
                            else:
                                report_dic[k] += v
                    break

            return report_dic


        else:
            error = "只支持文本文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_contents(self, request, shop, current_customer, dialog_contents):
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        robot_list = list(Servicer.objects.filter(category=0).values_list('name', flat=True))
        _q_dialog = DialogTB.objects.filter(shop=shop, customer=current_customer)
        if _q_dialog.exists():
            dialog_order = _q_dialog[0]
            end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
            if dialog_order.end_time == end_time:
                report_dic['discard'] += 1
                return report_dic
            dialog_order.end_time = end_time
            dialog_order.min += 1
        else:
            dialog_order = DialogTB()
            dialog_order.customer = current_customer
            dialog_order.shop = shop
            start_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
            end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
            dialog_order.start_time = start_time
            dialog_order.end_time = end_time
            dialog_order.min = 1
        try:
            dialog_order.creator = self.request.user.username
            dialog_order.save()
            report_dic['successful'] += 1
        except Exception as e:
            report_dic['error'].append(e)
            report_dic['false'] += 1
            return report_dic
        previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
        for dialog_content in dialog_contents:
            _q_dialog_detial = DialogTBDetail.objects.filter(sayer=dialog_content[0],
                                                          time=datetime.datetime.strptime
                                                          (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
            if _q_dialog_detial.exists():
                report_dic['discard'] += 1
                continue
            dialog_detial = DialogTBDetail()
            dialog_detial.order_status = 2
            dialog_detial.dialog = dialog_order
            dialog_detial.sayer = dialog_content[0]
            dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            dialog_detial.content = dialog_content[2]
            d_value = (dialog_detial.time - previous_time).seconds
            dialog_detial.interval = d_value
            previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            if dialog_content[0] == current_customer:
                dialog_detial.d_status = 0
            elif dialog_content[0] in robot_list:
                dialog_detial.d_status = 2
            else:
                dialog_detial.d_status = 1
                if re.match(r'^·客服.+', str(dialog_detial.content)):
                    dialog_detial.category = 1
                    dialog_detial.order_status = 1
                elif re.match(r'^·您好.+', str(dialog_detial.content)):
                    dialog_detial.category = 2
                    dialog_detial.order_status = 1
            try:
                dialog_detial.creator = self.request.user.username
                dialog_detial.save()
            except Exception as e:
                report_dic['error'].append(e)
        return report_dic


class DialogTBDetailSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogTBDetailSerializer
    filter_class = DialogTBDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_handler_dialogtbdetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBDetail.objects.none()
        queryset = DialogTBDetail.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogTBDetailFilter(params)
        serializer = DialogTBDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = DialogTBDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogTBDetail.objects.filter(id__in=order_ids, order_status=1)
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

        _rt_talk_title_new = ['order_category', 'goods_details', 'order_id', 'cs_information']
        _rt_talk_title_total = ['order_category', 'goods_details', 'order_id', 'cs_information',
                                'm_sn', 'broken_part', 'description']
        shop_list = Shop.objects.filter(platform_id__in=[1, 2])
        rt_shop_list = {}
        for shop in shop_list:
            rt_shop_list[shop.name] = shop
        jieba.load_userdict("apps/dfc/manualorder/addr_key_words.txt")
        if n:
            for obj in check_list:
                _check_talk_data = re.match(r'·客服.*', str(obj.content), re.DOTALL)
                if _check_talk_data:
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
                        order = ManualOrder()
                        _prefix = "TBDO"
                        serial_number = str(datetime.date.today()).replace("-", "")
                        obj.erp_order_id = serial_number + _prefix + str(obj.id)
                        order.erp_order_id = obj.erp_order_id
                        obj.save()
                    order.shop = rt_shop_list.get(obj.dialog.shop, None)
                    order.nickname = obj.dialog.customer
                    order.servicer = obj.sayer
                    _rt_talk_data = re.findall(r'{((?:.|\n)*?)}', str(obj.content), re.DOTALL)

                    if len(_rt_talk_data) == 4:
                        _rt_talk_dic = dict(zip(_rt_talk_title_new, _rt_talk_data))
                    elif len(_rt_talk_data) == 7:
                        _rt_talk_dic = dict(zip(_rt_talk_title_total, _rt_talk_data))
                    else:
                        n -= 1
                        data['error'].append("%s 对话的格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                    step_one_fields = ["order_category", "order_id", "m_sn", "broken_part", "description"]
                    for key_word in step_one_fields:
                        setattr(order, key_word, _rt_talk_dic.get(key_word, None))

                    all_info_element = re.split(r'(\d{11})', str(_rt_talk_dic["cs_information"]))
                    if len(all_info_element) < 3:
                        n -= 1
                        data['error'].append("%s 对话的客户信息格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                    elif len(all_info_element) == 3:
                        receiver, mobile, rt_address = all_info_element
                        if len(rt_address) < 8:
                            n -= 1
                            data['error'].append("%s 对话的客户信息格式不对，导致无法提取" % obj.id)
                            obj.mistake_tag = 3
                            obj.save()
                            continue
                    else:
                        receiver, mobile, *address = all_info_element
                        rt_address = reduce(lambda x, y: str(x) + str(y), address)
                    receiver = re.sub("(收件人)|(联系方式)|(手机)|:|：|(收货信息)|[!$%&\'()*+,-./:：;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", receiver)
                    order.receiver = receiver
                    order.mobile = mobile

                    _spilt_addr = PickOutAdress(rt_address)
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

                    try:
                        order.department = request.user.department
                        order.creator = request.user.username
                        order.save()
                    except Exception as e:
                        data["error"].append("%s 输出单保存出错: %s" % (obj.id, e))
                        n -= 1
                        obj.mistake_tag = 6
                        obj.save()
                        continue
                    goods_details = str(_rt_talk_dic["goods_details"]).split("+")
                    goods_list = []
                    if len(goods_details) == 1:
                        if "*" in _rt_talk_dic["goods_details"]:
                            goods_details = _rt_talk_dic["goods_details"].split("*")
                            _q_goods = Goods.objects.filter(name=str(goods_details[0]).strip())
                            if _q_goods.exists():
                                goods_list.append([_q_goods[0], str(goods_details[1]).strip()])
                            else:
                                data["error"].append("%s UT中不存在货品" % obj.id)
                                n -= 1
                                obj.mistake_tag = 7
                                obj.save()
                                continue
                        else:
                            data["error"].append("%s 货品错误（无乘号）" % obj.id)
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                    elif len(goods_details) > 1:
                        goods_details = list(map(lambda x: x.split("*"), goods_details))
                        goods_names = set(list(map(lambda x: x[0], goods_details)))
                        if len(goods_names) != len(goods_details):
                            data["error"].append("%s 明细中货品重复" % obj.id)
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
                            continue
                        mistake_tag = 0
                        for goods in goods_details:
                            if len(goods) == 2:
                                _q_goods = Goods.objects.filter(name=goods[0])
                                if _q_goods.exists():
                                    goods_list.append([_q_goods[0], str(goods[1]).strip()])
                                else:
                                    data["error"].append("%s UT中不存在此货品" % obj.id)
                                    n -= 1
                                    obj.mistake_tag = 7
                                    obj.save()
                                    mistake_tag = 1
                                    break
                            else:
                                data["error"].append("%s 货品错误" % obj.id)
                                n -= 1
                                obj.mistake_tag = 8
                                obj.save()
                                mistake_tag = 1
                                break
                        if mistake_tag:
                            continue
                    else:
                        data["error"].append("%s 货品错误" % obj.id)
                        n -= 1
                        obj.mistake_tag = 8
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
                            data["error"].append("%s 货品输出单保存出错" % obj.id)
                            n -= 1
                            obj.mistake_tag = 10
                            obj.save()
                            continue

                _check_talk_data = re.match(r'·您好.*', str(obj.content), re.DOTALL)
                if _check_talk_data:
                    compensation_data = re.findall(r'{((?:.|\n)*?)}', str(obj.content), re.DOTALL)
                    if len(compensation_data) == 7:
                        if obj.erp_order_id:
                            _q_repeat_order = Compensation.objects.filter(erp_order_id=obj.erp_order_id)
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
                                order = Compensation()
                                order.erp_order_id = obj.erp_order_id
                        else:
                            order = Compensation()
                            _prefix = "TBDC"
                            serial_number = str(datetime.date.today()).replace("-", "")
                            obj.erp_order_id = serial_number + _prefix + str(obj.id)
                            order.erp_order_id = obj.erp_order_id
                            obj.save()
                        order.nickname = obj.dialog.customer
                        for i in range(len(compensation_data)):
                            compensation_data[i] = re.sub('(型号)|(差价)|(姓名)|(支付宝)|(订单号)|(整机：)|(整机:)|(运费)|(补运费)', '', str(compensation_data[i]))
                        compensation_fields = ["goods_name", "compensation", "name", "alipay_id", "order_id", "formula", "order_category"]
                        compensation_dic = dict(zip(compensation_fields, compensation_data))
                        cs_error = 0
                        for key, value in compensation_dic.items():
                            if not value:
                                n -= 1
                                cs_error = 1
                                data["error"].append("%s 缺失必须要信息 %s" % (obj.id, key))
                                obj.mistake_tag = 11
                                obj.save()
                                break
                        if cs_error:
                            continue
                        _q_goods = Goods.objects.filter(name__icontains=compensation_dic["goods_name"])
                        if _q_goods.exists():
                            compensation_dic["goods_name"] = _q_goods[0]
                        else:
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                        if compensation_dic["order_category"] not in ['1', '3']:
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                        try:
                            elements = str(compensation_dic["formula"]).split("-", 1)
                            order.actual_receipts = float(elements[0])
                            transition = str(elements[1]).split("=")
                            order.receivable = float(transition[0])
                            order.checking = float(transition[1])
                            check_result = round(order.actual_receipts - order.receivable, 2)
                            if order.checking != check_result:
                                n -= 1
                                obj.mistake_tag = 13
                                obj.save()
                                continue
                            if float(compensation_dic["compensation"]) != check_result:
                                n -= 1
                                obj.mistake_tag = 14
                                obj.save()
                                continue
                        except Exception as e:
                            n -= 1
                            obj.mistake_tag = 13
                            obj.save()
                            continue
                        order_fields = ["goods_name", "compensation", "name", "alipay_id", "order_id", "order_category"]

                        for key_word in order_fields:
                            setattr(order, key_word, compensation_dic.get(key_word, None))
                        order.servicer = obj.sayer
                        order.shop = rt_shop_list.get(obj.dialog.shop, None)
                        order.nickname = obj.dialog.customer
                        try:
                            order.creator = request.user.username
                            order.save()
                        except Exception as e:
                            n -= 1
                            data['error'].append("保存差价申请单出错")
                            obj.mistake_tag = 15
                            obj.save()
                            continue
                    else:
                        n -= 1
                        data['error'].append("对话的格式不对，导致无法提取")
                        obj.mistake_tag = 1
                        obj.save()
                        continue

                obj.order_status = 2
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
            reject_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogTBDetailSubmitMyselfViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogTBDetailSerializer
    filter_class = DialogTBDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_user_dialogtbdetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBDetail.objects.none()
        queryset = DialogTBDetail.objects.filter(creator=self.request.user.username,order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["creator"] = user.username
        f = DialogTBDetailFilter(params)
        serializer = DialogTBDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = self.request.user.username
        if all_select_tag:
            handle_list = DialogTBDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogTBDetail.objects.filter(id__in=order_ids, creator=self.request.user.username, order_status=1)
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
        _rt_talk_title_new = ['order_category', 'goods_details', 'order_id', 'cs_information']
        _rt_talk_title_total = ['order_category', 'goods_details', 'order_id', 'cs_information',
                                'm_sn', 'broken_part', 'description']
        shop_list = Shop.objects.filter(platform_id__in=[1, 2])
        rt_shop_list = {}
        for shop in shop_list:
            rt_shop_list[shop.name] = shop
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        if n:
            for obj in check_list:
                _check_talk_data = re.match(r'·客服.*', str(obj.content), re.DOTALL)
                if _check_talk_data:
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
                        order = ManualOrder()
                        _prefix = "TBDO"
                        serial_number = str(datetime.date.today()).replace("-", "")
                        obj.erp_order_id = serial_number + _prefix + str(obj.id)
                        order.erp_order_id = obj.erp_order_id
                        obj.save()
                    order.shop = rt_shop_list.get(obj.dialog.shop, None)
                    order.nickname = obj.dialog.customer
                    order.servicer = obj.sayer
                    _rt_talk_data = re.findall(r'{((?:.|\n)*?)}', str(obj.content), re.DOTALL)

                    if len(_rt_talk_data) == 4:
                        _rt_talk_dic = dict(zip(_rt_talk_title_new, _rt_talk_data))
                    elif len(_rt_talk_data) == 7:
                        _rt_talk_dic = dict(zip(_rt_talk_title_total, _rt_talk_data))
                    else:
                        n -= 1
                        data['error'].append("%s 对话的格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                    step_one_fields = ["order_category", "servicer", "order_id", "m_sn", "broken_part", "description"]
                    for key_word in step_one_fields:
                        setattr(order, key_word, _rt_talk_dic.get(key_word, None))

                    all_info_element = re.split(r'(\d{11})', str(_rt_talk_dic["cs_information"]))
                    if len(all_info_element) < 3:
                        n -= 1
                        data['error'].append("%s 对话的客户信息格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                    elif len(all_info_element) == 3:
                        receiver, mobile, rt_address = all_info_element
                        if len(rt_address) < 8:
                            n -= 1
                            data['error'].append("%s 对话的客户信息格式不对，导致无法提取" % obj.id)
                            obj.mistake_tag = 3
                            obj.save()
                            continue
                    else:
                        receiver, mobile, *address = all_info_element
                        rt_address = reduce(lambda x, y: str(x) + str(y), address)
                    receiver = re.sub("(收件人)|(联系方式)|(手机)|:|：|(收货信息)|[!$%&\'()*+,-./:：;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", receiver)
                    order.receiver = receiver
                    order.mobile = mobile

                    _spilt_addr = PickOutAdress(rt_address)
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

                    try:
                        order.department = request.user.department
                        order.creator = request.user.username
                        order.save()
                    except Exception as e:
                        data["error"].append("%s 输出单保存出错: %s" % (obj.id, e))
                        n -= 1
                        obj.mistake_tag = 6
                        obj.save()
                        continue
                    goods_details = str(_rt_talk_dic["goods_details"]).split("+")
                    goods_list = []
                    if len(goods_details) == 1:
                        if "*" in _rt_talk_dic["goods_details"]:
                            goods_details = _rt_talk_dic["goods_details"].split("*")
                            _q_goods = Goods.objects.filter(name=str(goods_details[0]).strip())
                            if _q_goods.exists():
                                goods_list.append([_q_goods[0], str(goods_details[1]).strip()])
                            else:
                                data["error"].append("%s UT中不存在货品" % obj.id)
                                n -= 1
                                obj.mistake_tag = 7
                                obj.save()
                                continue
                        else:
                            data["error"].append("%s 货品错误（无乘号）" % obj.id)
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                    elif len(goods_details) > 1:
                        goods_details = list(map(lambda x: x.split("*"), goods_details))
                        goods_names = set(list(map(lambda x: x[0], goods_details)))
                        if len(goods_names) != len(goods_details):
                            data["error"].append("%s 明细中货品重复" % obj.id)
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
                            continue
                        mistake_tag = 0
                        for goods in goods_details:
                            if len(goods) == 2:
                                _q_goods = Goods.objects.filter(name=goods[0])
                                if _q_goods.exists():
                                    goods_list.append([_q_goods[0], str(goods[1]).strip()])
                                else:
                                    data["error"].append("%s UT中不存在此货品" % obj.id)
                                    n -= 1
                                    obj.mistake_tag = 7
                                    obj.save()
                                    mistake_tag = 1
                                    break
                            else:
                                data["error"].append("%s 货品错误" % obj.id)
                                n -= 1
                                obj.mistake_tag = 8
                                obj.save()
                                mistake_tag = 1
                                break
                        if mistake_tag:
                            continue
                    else:
                        data["error"].append("%s 货品错误" % obj.id)
                        n -= 1
                        obj.mistake_tag = 8
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
                            data["error"].append("%s 货品输出单保存出错" % obj.id)
                            n -= 1
                            obj.mistake_tag = 10
                            obj.save()
                            continue

                _check_talk_data = re.match(r'·您好.*', str(obj.content), re.DOTALL)
                if _check_talk_data:
                    compensation_data = re.findall(r'{((?:.|\n)*?)}', str(obj.content), re.DOTALL)
                    if len(compensation_data) == 7:
                        if obj.erp_order_id:
                            _q_repeat_order = Compensation.objects.filter(erp_order_id=obj.erp_order_id)
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
                                order = Compensation()
                                order.erp_order_id = obj.erp_order_id
                        else:
                            order = Compensation()
                            _prefix = "TBDC"
                            serial_number = str(datetime.date.today()).replace("-", "")
                            obj.erp_order_id = serial_number + _prefix + str(obj.id)
                            order.erp_order_id = obj.erp_order_id
                            obj.save()
                        for i in range(len(compensation_data)):
                            compensation_data[i] = re.sub('(型号)|(差价)|(姓名)|(支付宝)|(订单号)|(整机：)|(整机:)|(退款)', '', str(compensation_data[i]))
                        compensation_fields = ["goods_name", "compensation", "name", "alipay_id", "order_id", "formula", "order_category"]
                        compensation_dic = dict(zip(compensation_fields, compensation_data))
                        cs_error = 0
                        for key, value in compensation_dic.items():
                            if not value:
                                n -= 1
                                cs_error = 1
                                data["error"].append("%s 缺失必须要信息 %s" % (obj.id, key))
                                obj.mistake_tag = 11
                                obj.save()
                                break
                        if cs_error:
                            continue
                        _q_goods = Goods.objects.filter(name__icontains=compensation_dic["goods_name"])
                        if _q_goods.exists():
                            compensation_dic["goods_name"] = _q_goods[0]
                        else:
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                        if compensation_dic["order_category"] not in ['1', '3']:
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                        try:
                            elements = str(compensation_dic["formula"]).split("-", 1)
                            order.actual_receipts = float(elements[0])
                            transition = str(elements[1]).split("=")
                            order.receivable = float(transition[0])
                            order.checking = float(transition[1])
                            check_result = round(order.actual_receipts - order.receivable, 2)
                            if order.checking != check_result:
                                n -= 1
                                obj.mistake_tag = 13
                                obj.save()
                                continue
                            if float(compensation_dic["compensation"]) != check_result:
                                n -= 1
                                obj.mistake_tag = 14
                                obj.save()
                                continue
                        except Exception as e:
                            n -= 1
                            obj.mistake_tag = 13
                            obj.save()
                            continue
                        order_fields = ["goods_name", "compensation", "name", "alipay_id", "order_id", "order_category"]

                        for key_word in order_fields:
                            setattr(order, key_word, compensation_dic.get(key_word, None))
                        order.servicer = obj.sayer
                        order.shop = rt_shop_list.get(obj.dialog.shop, None)
                        order.nickname = obj.dialog.customer
                        try:
                            order.creator = request.user.username
                            order.save()
                        except Exception as e:
                            data['error'].append("保存差价申请单出错")
                            obj.mistake_tag = 15
                            obj.save()
                            continue
                    else:
                        n -= 1
                        data['error'].append("对话的格式不对，导致无法提取")
                        obj.mistake_tag = 1
                        obj.save()
                        continue

                obj.order_status = 2
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
            reject_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogTBDetailViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogTBDetailSerializer
    filter_class = DialogTBDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogtbdetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBDetail.objects.none()
        queryset = DialogTBDetail.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DialogTBDetailFilter(params)
        serializer = DialogTBDetailSerializer(f.qs[:3000], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DialogTBDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogTBDetail.objects.filter(id__in=order_ids, order_status=2)
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogTBWordsViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogTBWordsSerializer
    filter_class = DialogTBWordsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogtbwords']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBWords.objects.none()
        queryset = DialogTBWords.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogTBWordsFilter(params)
        serializer = DialogTBWordsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogTBWordsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogTBWords.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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


class DialogJDViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogJDSerializer
    filter_class = DialogJDFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogjd']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJD.objects.none()
        queryset = DialogJD.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DialogJDFilter(params)
        serializer = DialogJDSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = DialogJDFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogJD.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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
                    order = ManualOrder()
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
                                _q_district_again = District.objects.filter(province=order.province,
                                                                            name__contains=words)
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
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):

        ALLOWED_EXTENSIONS = ['log']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            start_tag = 0

            dialog_contents = []
            dialog_content = []
            i = 0
            content = ''
            shop = ''
            try:
                shop_qj = "小狗京东商城店铺FBP"
                shop_zy = "小狗京东自营"
            except Exception as e:
                report_dic["error"] = "必须创建京东店铺才可以导入"
                return report_dic
            fbp_servicer_list = list(Servicer.objects.filter(shop__name=shop_qj).values_list("name", flat=True))
            zy_servicer_list = list(Servicer.objects.filter(shop__name=shop_zy).values_list("name", flat=True))
            all_servicer_list = fbp_servicer_list + zy_servicer_list
            servicer_list = list(Servicer.objects.filter(category=1).values_list('name', flat=True))
            robot_list = list(Servicer.objects.filter(category=0).values_list('name', flat=True))
            while True:
                i += 1
                data_line = _file.readline().decode('utf8')
                if not data_line:
                    break
                if re.match(r'^\/\*{17}以下为一通会话', data_line):
                    start_tag = 1
                    continue
                if re.match(r'^\/\*{17}会话结束', data_line):
                    if content:
                        dialog_content.append(content)
                        if len(dialog_content) == 3:
                            dialog_contents.append(dialog_content)
                        dialog_content = []
                    if dialog_contents:
                        for current_content in dialog_contents:
                            test_name = current_content[0]
                            if test_name not in all_servicer_list:
                                customer = test_name
                                break
                        if not customer:
                            report_dic['error'].append('客户无回应留言丢弃。 %s' % e)
                            dialog_contents.clear()
                            dialog_content.clear()
                            content = ''
                            continue
                    else:
                        report_dic['error'].append('对话主体就一句话，或者文件格式出现错误！')
                        dialog_contents.clear()
                        dialog_content.clear()
                        content = ''
                        continue
                    if not shop:
                        dialog_contents.clear()
                        dialog_content.clear()
                        report_dic['error'].append('店铺出现错误，检查源文件！')
                        break

                    _q_dialog = DialogJD.objects.filter(shop=shop, customer=customer)
                    if _q_dialog.exists():
                        dialog_order = _q_dialog[0]
                        try:
                            end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            report_dic['error'].append(e)
                            continue
                        if dialog_order.end_time == end_time:
                            report_dic['discard'] += 1
                            dialog_contents.clear()
                            dialog_content.clear()
                            content = ''
                            start_tag = 0
                            continue
                        dialog_order.end_time = end_time
                        dialog_order.min += 1
                    else:
                        dialog_order = DialogJD()
                        dialog_order.customer = customer
                        dialog_order.shop = shop
                        try:
                            start_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
                            end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            report_dic['error'].append(e)
                            continue
                        dialog_order.start_time = start_time
                        dialog_order.end_time = end_time
                        dialog_order.min = 1
                    try:
                        dialog_order.creator = self.request.user.username
                        dialog_order.save()
                        report_dic['successful'] += 1
                    except Exception as e:
                        report_dic['error'].append(e)
                        report_dic['false'] += 1
                        dialog_contents.clear()
                        dialog_content.clear()
                        content = ''
                        start_tag = 0
                        continue
                    previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
                    for dialog_content in dialog_contents:
                        # 屏蔽机器人对话
                        current_sayer = str(dialog_content[0]).replace(' ', '')
                        _q_dialog_detial = DialogJDDetail.objects.filter(sayer=current_sayer,
                                                                      time=datetime.datetime.strptime
                                                                      (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
                        if _q_dialog_detial.exists():
                            continue

                        dialog_detial = DialogJDDetail()
                        dialog_detial.order_status = 2
                        dialog_detial.dialog = dialog_order
                        dialog_detial.sayer = current_sayer
                        dialog_detial.content = str(dialog_content[2])
                        if current_sayer in robot_list:
                            dialog_detial.d_status = 2
                        elif current_sayer in servicer_list:
                            dialog_detial.d_status = 1
                            if re.match(r'^·客服.+', dialog_detial.content):
                                dialog_detial.category = 1
                                dialog_detial.order_status = 1
                        try:
                            dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]).strip(), '%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            report_dic['error'].append(e)
                            continue
                        dialog_detial.interval = (dialog_detial.time - previous_time).seconds
                        previous_time = dialog_detial.time
                        try:
                            dialog_detial.creator = self.request.user.username
                            dialog_detial.save()
                        except Exception as e:
                            report_dic['error'].append(e)
                    dialog_contents.clear()
                    dialog_content.clear()
                    content = ''
                    start_tag = 0
                    continue
                if start_tag:
                    dialog = re.findall(r'(.*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', str(data_line))
                    info = str(data_line).split(' ')
                    num = len(info)
                    if dialog and num == 3:
                        if content:
                            dialog_content.append(content)
                            if len(dialog_content) == 3:
                                dialog_contents.append(dialog_content)
                            dialog_content = []
                        _sayer = str(dialog[0][0]).replace(" ", "")

                        if not shop:
                            if _sayer in fbp_servicer_list:
                                shop = shop_qj
                            elif _sayer in zy_servicer_list:
                                shop = shop_zy

                        dialog_content.append(_sayer)
                        dialog_content.append(dialog[0][1])
                        if _sayer not in servicer_list and re.match('^小狗.+', _sayer):
                            try:
                                servicer_new = Servicer()
                                servicer_new.name = _sayer
                                servicer_new.category = 1
                                servicer_new.shop = Shop.objects.filter(name=shop)[0]
                                servicer_new.save()
                            except:
                                report_dic["error"].append("先设置好新客服，再导入")
                                break
                            servicer_list.append(_sayer.name)
                        content = ''
                    else:
                        content = '%s%s' % (content, str(data_line))

            return report_dic


        else:
            error = "只支持文本文件格式！"
            report_dic["error"].append(error)
            return report_dic



class DialogJDDetailSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogJDDetailSerializer
    filter_class = DialogJDDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogjddetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJDDetail.objects.none()
        queryset = DialogJDDetail.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogJDDetailFilter(params)
        serializer = DialogJDDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogJDDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogJDDetail.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def collect(self, request, *args, **kwargs):
        params = request.data
        collect_list = self.get_handle_list(params)
        n = len(collect_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        shop_zy = Shop.objects.filter(name="小狗京东自营")[0]
        shop_pop = Shop.objects.filter(name="小狗京东商城店铺FBP")[0]
        rt_shop_list = {
            "小狗京东自营": shop_zy,
            "小狗京东商城店铺FBP": shop_pop
        }

        _rt_talk_title_new = ['order_category', 'goods_details', 'order_id', 'cs_information']
        _rt_talk_title_total = ['order_category', 'goods_details', 'order_id', 'cs_information',
                                'm_sn', 'broken_part', 'description']
        if n:
            for obj in collect_list:
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
                    order = ManualOrder()
                    _prefix = "JDDO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                    order.erp_order_id = obj.erp_order_id
                    obj.save()
                order.shop = rt_shop_list.get(obj.dialog.shop, None)
                order.nickname = obj.dialog.customer
                order.servicer = obj.sayer
                _check_talk_data = re.match(r'·客服.*', str(obj.content), re.DOTALL)
                if _check_talk_data:
                    _rt_talk_data = re.findall(r'{((?:.|\n)*?)}', str(obj.content), re.DOTALL)

                    if len(_rt_talk_data) == 4:
                        _rt_talk_dic = dict(zip(_rt_talk_title_new, _rt_talk_data))
                    elif len(_rt_talk_data) == 7:
                        _rt_talk_dic = dict(zip(_rt_talk_title_total, _rt_talk_data))
                    else:
                        n -= 1
                        data['false'] += 1
                        data['error'].append("%s 对话的格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                    step_one_fields = ["order_category", "order_id", "m_sn", "broken_part", "description"]
                    for key_word in step_one_fields:
                        setattr(order, key_word, _rt_talk_dic.get(key_word, None))

                    all_info_element = re.split(r'(\d{11})', str(_rt_talk_dic["cs_information"]))
                    if len(all_info_element) < 3:
                        n -= 1
                        data['false'] += 1
                        data['error'].append("%s 对话的客户信息格式不对，导致无法提取" % obj.id)
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                    elif len(all_info_element) == 3:
                        receiver, mobile, rt_address = all_info_element
                    else:
                        receiver, mobile, *address = all_info_element
                        rt_address = reduce(lambda x, y: str(x) + str(y), address)
                    receiver = re.sub("(收件人)|(联系方式)|(手机)|:|：|(收货信息)|[!$%&\'()*+,-./:：;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", receiver)
                    order.receiver = receiver
                    order.mobile = mobile

                    _spilt_addr = PickOutAdress(rt_address)
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

                    try:
                        order.department = request.user.department
                        order.creator = request.user.username
                        order.save()
                    except Exception as e:
                        data["error"].append("%s 输出单保存出错: %s" % (obj.id, e))
                        n -= 1
                        obj.mistake_tag = 6
                        obj.save()
                        continue
                    goods_details = str(_rt_talk_dic["goods_details"]).split("+")
                    goods_list = []
                    if len(goods_details) == 1:
                        if "*" in _rt_talk_dic["goods_details"]:
                            goods_details = _rt_talk_dic["goods_details"].split("*")
                            _q_goods = Goods.objects.filter(name=goods_details[0])
                            if _q_goods.exists():
                                goods_list.append([_q_goods[0], str(goods_details[1]).strip()])
                            else:
                                data["error"].append("%s UT中不存在货品" % obj.id)
                                n -= 1
                                obj.mistake_tag = 7
                                obj.save()
                                continue
                        else:
                            data["error"].append("%s 货品错误（无乘号）" % obj.id)
                            n -= 1
                            obj.mistake_tag = 8
                            obj.save()
                            continue
                    elif len(goods_details) > 1:
                        goods_details = list(map(lambda x: x.split("*"), goods_details))
                        goods_names = set(list(map(lambda x: x[0], goods_details)))
                        if len(goods_names) != len(goods_details):
                            data["error"].append("%s 明细中货品重复" % obj.id)
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
                            continue
                        for goods in goods_details:
                            if len(goods) == 2:
                                _q_goods = Goods.objects.filter(name=goods[0])
                                if _q_goods.exists():
                                    goods_list.append([_q_goods[0], str(goods[1]).strip()])
                                else:
                                    data["error"].append("%s UT中不存在此货品" % obj.id)
                                    n -= 1
                                    obj.mistake_tag = 7
                                    obj.save()
                                    continue
                            else:
                                data["error"].append("%s 货品错误" % obj.id)
                                n -= 1
                                obj.mistake_tag = 8
                                obj.save()
                                continue
                    else:
                        data["error"].append("%s 货品错误" % obj.id)
                        n -= 1
                        obj.mistake_tag = 8
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
                            data["error"].append("%s 货品输出单保存出错" % obj.id)
                            n -= 1
                            obj.mistake_tag = 10
                            obj.save()
                            continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(collect_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def abandon(self, request, *args, **kwargs):
        params = request.data
        abandon_list = self.get_handle_list(params)
        n = len(abandon_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            abandon_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可丢弃的单据！")
        data["successful"] = n
        return Response(data)


class DialogJDDetailViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogJDDetailSerializer
    filter_class = DialogJDDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogjddetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJDDetail.objects.none()
        queryset = DialogJDDetail.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogJDDetailFilter(params)
        serializer = DialogJDDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DialogJDDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogJDDetail.objects.filter(id__in=order_ids, order_status=2)
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogJDWordsViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogJDWordsSerializer
    filter_class = DialogJDWordsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogjdwords']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJDWords.objects.none()
        queryset = DialogJDWords.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = DialogJDWordsFilter(params)
        serializer = DialogJDWordsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DialogJDWordsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogJDWords.objects.filter(id__in=order_ids, order_status=2)
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogOWViewsetSubmit(viewsets.ModelViewSet):
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
    serializer_class = DialogOWSerializer
    filter_class = DialogOWFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogow']
    }

    def get_queryset(self):
        if not self.request:
            return DialogOW.objects.none()
        queryset = DialogOW.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogOWFilter(params)
        serializer = DialogOWSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = DialogOWFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogOW.objects.filter(id__in=order_ids, order_status=1)
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
        category_list = {
            "质量问题": 1,
            "开箱即损": 2,
            "礼品赠品": 3,
        }

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
                obj.mobile = str(obj.mobile).strip()
                if not re.match(r"^1[3456789]\d{9}$", obj.mobile):
                    data["error"].append("%s 手机错误" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                else:
                    order.mobile = obj.mobile

                order.address = str(obj.area) + str(obj.address)

                _spilt_addr = PickOutAdress(order.address)
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

                order.nickname = obj.customer
                order_fields = ["receiver", "m_sn", "broken_part", "description", "servicer"]
                for key_word in order_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

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
                        _q_goods = Goods.objects.filter(name=goods_details[0])
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
                            _q_goods = Goods.objects.filter(name=goods[0])
                            if _q_goods.exists():
                                goods_list.append([_q_goods[0], str(goods[1]).strip()])
                            else:
                                data["error"].append("%s 货品错误" % obj.id)
                                n -= 1
                                obj.mistake_tag = 9
                                obj.save()
                                continue
                        else:
                            data["error"].append("%s 货品错误" % obj.id)
                            n -= 1
                            obj.mistake_tag = 9
                            obj.save()
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
                obj.order_status = 2
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
            reject_list.update(order_status=2)
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
            "会话ID": "call_id",
            "访客进入时间": "guest_entry_time",
            "会话开始时间": "call_start_time",
            "客服首次响应时长": "first_response_time",
            "客服平均响应时长": "average_response_time",
            "访客排队时长": "queue_time",
            "会话时长": "call_duration",
            "会话终止方": "ender",
            "客服解决状态": "call_status",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "接待客服": "servicer",
            "访客用户名": "customer",
            "满意度": "satisfaction",
            "对话回合数": "rounds",
            "来源终端": "source",
            "会话内容": "content",
            "产品型号": "goods_type",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "省市区": "area",
            "出厂序列号": "m_sn",
            "详细地址": "address",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "建单手机": "mobile",
            "收件人姓名": "receiver"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["会话ID", "访客进入时间", "会话开始时间", "客服首次响应时长", "客服平均响应时长", "访客排队时长",
                             "会话时长", "会话终止方", "客服解决状态", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "接待客服", "访客用户名", "满意度", "对话回合数", "来源终端", "会话内容", "产品型号", "购买日期",
                             "购买店铺", "省市区", "出厂序列号", "详细地址", "补寄原因", "配件信息", "损坏部位",
                             "损坏描述", "建单手机", "收件人姓名"]

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
            _ret_verify_field = DialogOW.verify_mandatory(columns_key)
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
            _q_dialog = DialogOW.objects.filter(call_id=row["call_id"])
            if _q_dialog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = DialogOW()
            order.shop = "小狗官方商城"
            order_fields = ["call_id", "guest_entry_time", "call_start_time", "first_response_time",
                            "average_response_time", "queue_time", "call_duration", "ender", "call_status",
                            "primary_classification", "secondary_classification", "three_level_classification",
                            "four_level_classification", "five_level_classification", "servicer", "customer",
                            "satisfaction", "rounds", "source", "goods_type", "purchase_time",
                            "area", "m_sn", "address", "order_category", "broken_part", "goods_details",
                            "description", "mobile", "receiver"]
            for field in order_fields:
                setattr(order, field, row[field])
            order.order_status = 2
            judgment_dic = defaultdict(list)
            judgment_fields = ["address", "mobile", "receiver", "goods_details"]
            for key_words in judgment_fields:
                if str(row[key_words]) == "nan":
                    row[key_words] = "--"
            _pre_dic = dict([(key, row[key]) for key in judgment_fields])
            for (key, value) in _pre_dic.items():
                judgment_dic[value].append(key)
            if len(judgment_dic.get("--", [])) < 2:
                order.is_order = True
                order.order_status = 1
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1
            dialog_content = []
            dialog_contents = []
            start_tag = 0

            if row["content"] and row["content"] != "--":
                contents = str(row["content"]).split("\n")
                contents_length = len(contents)-1
                i = 0
                for content in contents:
                    i += 1
                    if order.servicer[:3] in content[:3] or order.customer[:3] in content[:3]:
                        if len(dialog_content) == 3:
                            dialog_contents.append(dialog_content)
                            dialog_content = []
                        else:
                            dialog_content = []
                        start_tag = 0
                        content = content.split("    ")
                        if len(content) == 2:
                            dialog_content.append(content[0])
                            dialog_content.append(re.sub("[年月]", "-", content[1]).replace("日", ""))
                            start_tag = 1
                            continue
                    if start_tag:
                        if dialog_content:
                            dialog_content.append(content)
                    if i == contents_length:
                        if len(dialog_content) == 3:
                            dialog_contents.append(dialog_content)
                            dialog_content = []
                        else:
                            dialog_content = []
                previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')

                for dialog_content in dialog_contents:
                    dialog_detial = DialogOWDetail()
                    dialog_detial.dialog = order
                    dialog_detial.sayer = dialog_content[0].strip()
                    dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1].strip()), '%Y-%m-%d %H:%M:%S')
                    dialog_detial.content = dialog_content[2]
                    d_value = (dialog_detial.time - previous_time).seconds
                    dialog_detial.interval = d_value
                    previous_time = dialog_detial.time
                    if dialog_content[0] == order.customer:
                        dialog_detial.d_status = 1
                    else:
                        dialog_detial.d_status = 0
                    try:
                        dialog_detial.creator = request.user.username
                        dialog_detial.save()
                    except Exception as e:
                        report_dic['error'].append(e)

        return report_dic


class DialogOWViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogOWSerializer
    filter_class = DialogOWFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogow']
    }

    def get_queryset(self):
        if not self.request:
            return DialogOW.objects.none()
        queryset = DialogOW.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = DialogOWFilter(params)
        serializer = DialogOWSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DialogOWFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogOW.objects.filter(id__in=order_ids, order_status=2)
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DialogOWDetailSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogOWDetailSerializer
    filter_class = DialogOWDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogowdetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogOWDetail.objects.none()
        queryset = DialogOWDetail.objects.filter(extract_tag=False, category__in=[1, 2]).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogOWDetailFilter(params)
        serializer = DialogOWDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogOWDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogOWDetail.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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


class DialogOWDetailViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogOWDetailSerializer
    filter_class = DialogOWDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dialog.view_dialogowdetail']
    }

    def get_queryset(self):
        if not self.request:
            return DialogOWDetail.objects.none()
        queryset = DialogOWDetail.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogOWDetailFilter(params)
        serializer = DialogOWDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogOWDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogOWDetail.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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
                    order = ManualOrder()
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
                                _q_district_again = District.objects.filter(province=order.province,
                                                                            name__contains=words)
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


class DialogOWWordsViewset(viewsets.ModelViewSet):
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
    serializer_class = DialogOWWordsSerializer
    filter_class = DialogOWWordsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    # extra_perm_map = {
    #     "GET": ['dialog.view_dialogowwords']
    # }

    def get_queryset(self):
        if not self.request:
            return DialogOWWords.objects.none()
        queryset = DialogOWWords.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogOWWordsFilter(params)
        serializer = DialogOWWordsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogOWWordsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogOWWords.objects.filter(id__in=order_ids, order_status=1)
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
                                '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三沙市', '琼中黎族苗族自治县', '琼海市',
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
                    order = ManualOrder()
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
                                _q_district_again = District.objects.filter(province=order.province,
                                                                            name__contains=words)
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
