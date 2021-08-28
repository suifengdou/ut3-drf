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
        "GET": ['shop.view_shop']
    }


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
        "GET": ['woinvoice.view_invoice']
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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

    # def handle_upload_file(self, _file):
    #
    #     ALLOWED_EXTENSIONS = ['txt']
    #     report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
    #
    #     if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
    #         start_tag = 0
    #
    #         dialog_contents = []
    #         dialog_content = []
    #         i = 0
    #         while True:
    #             i += 1
    #             try:
    #                 data_line = _file.readline().decode('gbk')
    #             except Exception as e:
    #                 continue
    #
    #             if i == 1:
    #                 try:
    #                     info = str(data_line).strip().replace('\n', '').replace('\r', '')
    #                     if ":" in info:
    #                         info = info.split(":")[0]
    #                     shop = info
    #                     if not shop:
    #                         report_dic['error'].append('请使用源表进行导入，不要对表格进行处理。')
    #                         break
    #                     continue
    #                 except Exception as e:
    #                     report_dic['error'].append('请使用源表进行导入，不要对表格进行处理。')
    #                     break
    #
    #             customer = re.findall(r'^-{28}(.*)-{28}', data_line)
    #             if customer:
    #                 if dialog_content:
    #                     dialog_contents.append(dialog_content)
    #                     dialog_content = []
    #                 if dialog_contents:
    #                     _q_dialog = DialogTB.objects.filter(shop=shop, customer=current_customer)
    #                     if _q_dialog.exists():
    #                         dialog_order = _q_dialog[0]
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_order.end_time == end_time:
    #                             report_dic['discard'] += 1
    #                             current_customer = customer[0]
    #                             dialog_contents.clear()
    #                             dialog_content.clear()
    #                             continue
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min += 1
    #                     else:
    #                         dialog_order = DialogTB()
    #                         dialog_order.customer = current_customer
    #                         dialog_order.shop = shop
    #                         start_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_order.start_time = start_time
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min = 1
    #                     try:
    #                         dialog_order.creator = self.request.user.username
    #                         dialog_order.save()
    #                         report_dic['successful'] += 1
    #                     except Exception as e:
    #                         report_dic['error'].append(e)
    #                         report_dic['false'] += 1
    #                         dialog_contents.clear()
    #                         dialog_content.clear()
    #                         current_customer = customer[0]
    #                         continue
    #                     previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                     for dialog_content in dialog_contents:
    #                         _q_dialog_detial = DialogTBDetail.objects.filter(sayer=dialog_content[0],
    #                                                                       time=datetime.datetime.strptime
    #                                                                       (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
    #                         if _q_dialog_detial.exists():
    #                             report_dic['discard'] += 1
    #                             continue
    #                         dialog_detial = DialogTBDetail()
    #                         dialog_detial.dialog_tb = dialog_order
    #                         dialog_detial.sayer = dialog_content[0]
    #                         dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_detial.content = dialog_content[2]
    #                         d_value = (dialog_detial.time - previous_time).seconds
    #                         dialog_detial.interval = d_value
    #                         previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_content[0] == current_customer:
    #                             dialog_detial.d_status = 1
    #                         else:
    #                             dialog_detial.d_status = 0
    #                         try:
    #                             dialog_detial.creator = self.request.user.username
    #                             dialog_detial.save()
    #                         except Exception as e:
    #                             report_dic['error'].append(e)
    #                     dialog_contents.clear()
    #                     dialog_content.clear()
    #                     current_customer = customer[0]
    #                 else:
    #                     current_customer = customer[0]
    #                 start_tag = 1
    #                 continue
    #             if start_tag:
    #                 dialog = re.findall(r'(.*)(\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\):  )(.*)', str(data_line))
    #
    #                 if dialog:
    #                     if len(dialog[0]) == 3:
    #                         if dialog_content:
    #                             dialog_contents.append(dialog_content)
    #                             dialog_content = []
    #                         sayer = dialog[0][0]
    #                         sayer = re.sub("cntaobao", "", str(sayer))
    #                         dialog_content.append(sayer)
    #                         dialog_content.append(str(dialog[0][1]).replace('(', '').replace('):  ', ''))
    #                         dialog_content.append(str(dialog[0][2]))
    #                 else:
    #                     # 这一块需要重新调试看看是干啥呢
    #                     try:
    #                         dialog_content[2] = '%s%s' % (dialog_content[2], str(data_line))
    #
    #                     except Exception as e:
    #                         report_dic['error'].append(e)
    #
    #             if re.match(r'^={64}', str(data_line)):
    #                 if dialog_content:
    #                     dialog_contents.append(dialog_content)
    #                     dialog_content = []
    #                 if dialog_contents:
    #                     _q_dialog = DialogTB.objects.filter(shop=shop, customer=current_customer)
    #                     if _q_dialog.exists():
    #                         dialog_order = _q_dialog[0]
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_order.end_time >= end_time:
    #                             report_dic['discard'] += 1
    #                             continue
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min += 1
    #                     else:
    #                         dialog_order = DialogTB()
    #                         dialog_order.customer = current_customer
    #                         dialog_order.shop = shop
    #                         start_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_order.start_time = start_time
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min = 1
    #                     try:
    #                         dialog_order.creator = self.request.user.username
    #                         dialog_order.save()
    #                         report_dic['successful'] += 1
    #                     except Exception as e:
    #                         report_dic['error'].append(e)
    #                         report_dic['false'] += 1
    #                         continue
    #                     previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                     for dialog_content in dialog_contents:
    #                         _q_dialog_detial = DialogTBDetail.objects.filter(sayer=dialog_content[0],
    #                                                                       time=datetime.datetime.strptime
    #                                                                       (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
    #                         if _q_dialog_detial.exists():
    #                             report_dic['discard'] += 1
    #                             continue
    #                         dialog_detial = DialogTBDetail()
    #                         dialog_detial.dialog_tb = dialog_order
    #                         dialog_detial.sayer = dialog_content[0]
    #                         dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_detial.content = dialog_content[2]
    #                         d_value = (dialog_detial.time - previous_time).seconds
    #                         dialog_detial.interval = d_value
    #                         previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_content[0] == current_customer:
    #                             dialog_detial.d_status = 1
    #                         else:
    #                             dialog_detial.d_status = 0
    #                         try:
    #                             dialog_detial.creator = self.request.user.username
    #                             dialog_detial.save()
    #                         except Exception as e:
    #                             report_dic['error'].append(e)
    #                     start_tag = 0
    #             if not data_line:
    #                 if dialog_contents:
    #                     _q_dialog = DialogTB.objects.filter(shop=shop, customer=current_customer)
    #                     if _q_dialog.exists():
    #                         dialog_order = _q_dialog[0]
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_order.end_time >= end_time:
    #                             report_dic['discard'] += 1
    #                             continue
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min += 1
    #                     else:
    #                         dialog_order = DialogTB()
    #                         dialog_order.customer = current_customer
    #                         dialog_order.shop = shop
    #                         start_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                         end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_order.start_time = start_time
    #                         dialog_order.end_time = end_time
    #                         dialog_order.min = 1
    #                     try:
    #                         dialog_order.creator = self.request.user.username
    #                         dialog_order.save()
    #                         report_dic['successful'] += 1
    #                     except Exception as e:
    #                         report_dic['error'].append(e)
    #                         report_dic['false'] += 1
    #                         continue
    #                     previous_time = datetime.datetime.strptime(str(dialog_contents[0][1]), '%Y-%m-%d %H:%M:%S')
    #                     for dialog_content in dialog_contents:
    #                         _q_dialog_detial = DialogTBDetail.objects.filter(sayer=dialog_content[0],
    #                                                                       time=datetime.datetime.strptime
    #                                                                       (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
    #                         if _q_dialog_detial.exists():
    #                             report_dic['discard'] += 1
    #                             continue
    #                         dialog_detial = DialogTBDetail()
    #                         dialog_detial.dialog_tb = dialog_order
    #                         dialog_detial.sayer = dialog_content[0]
    #                         dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         dialog_detial.content = dialog_content[2]
    #                         d_value = (dialog_detial.time - previous_time).seconds
    #                         dialog_detial.interval = d_value
    #                         previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
    #                         if dialog_content[0] == current_customer:
    #                             dialog_detial.d_status = 1
    #                         else:
    #                             dialog_detial.d_status = 0
    #                         try:
    #                             dialog_detial.creator = self.request.user.username
    #                             dialog_detial.save()
    #                         except Exception as e:
    #                             report_dic['error'].append(e)
    #                 break
    #
    #         return report_dic
    #
    #
    #     else:
    #         error = "只支持文本文件格式！"
    #         report_dic["error"].append(error)
    #         return report_dic
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
            dialog_detial.dialog = dialog_order
            dialog_detial.sayer = dialog_content[0]
            dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            dialog_detial.content = dialog_content[2]
            d_value = (dialog_detial.time - previous_time).seconds
            dialog_detial.interval = d_value
            previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            if dialog_content[0] == current_customer:
                dialog_detial.d_status = 1
            else:
                dialog_detial.d_status = 0
                if re.match(r'^·客服.+', str(dialog_detial.content)):
                    dialog_detial.category = 1
                elif re.match(r'^·您好.+', str(dialog_detial.content)):
                    dialog_detial.category = 2
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
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBDetail.objects.none()
        queryset = DialogTBDetail.objects.filter(extract_tag=False, category__in=[1, 2]).order_by("-id")
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
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DialogTBDetail.objects.none()
        queryset = DialogTBDetail.objects.filter(creator=self.request.user.username, extract_tag=False, category__in=[1, 2]).order_by("-id")
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
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
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
        params["order_status"] = 1
        f = DialogTBDetailFilter(params)
        serializer = DialogTBDetailSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
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
        params["order_status"] = 1
        f = DialogJDFilter(params)
        serializer = DialogJDSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
                shop_qj = Shop.objects.filter(name="小狗京东商城店铺FBP")[0]
                shop_zy = Shop.objects.filter(name="小狗京东自营")[0]
            except Exception as e:
                report_dic["error"] = "必须创建京东店铺才可以导入"
                return report_dic
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
                    if dialog_contents:
                        for current_content in dialog_contents:
                            test_name = current_content[0]
                            if test_name not in servicer_list and test_name not in robot_list:
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
                        dialog_detial.dialog = dialog_order
                        dialog_detial.sayer = current_sayer
                        if current_sayer in robot_list:
                            dialog_detial.d_status = 2
                        if current_sayer in servicer_list:
                            dialog_detial.d_status = 1

                        try:
                            dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
                        except Exception as e:
                            report_dic['error'].append(e)
                            continue
                        d_value = (dialog_detial.time - previous_time).seconds
                        dialog_detial.interval = d_value
                        previous_time = dialog_detial.time
                        dialog_detial.content = str(dialog_content[2])
                        if re.match(r'^·客服.+', dialog_detial.content):
                            dialog_detial.category = 1
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
                        _shop_list = {
                            '小狗旗舰': shop_qj,
                            '小狗自营': shop_zy,
                        }
                        if content:
                            dialog_content.append(content)
                            if len(dialog_content) == 3:
                                dialog_contents.append(dialog_content)
                            dialog_content = []
                        _sayer = str(dialog[0][0]).replace(" ", "")
                        dialog_content.append(_sayer)
                        dialog_content.append(dialog[0][1])
                        if _sayer not in servicer_list and re.match('^小狗.+', _sayer):
                            _shop_word = _sayer[:4]
                            shop_servicer = _shop_list.get(_shop_word, None)
                            servicer_new = Servicer()
                            servicer_new.name = _sayer
                            servicer_new.category = 1
                            servicer_new.shop = shop_servicer
                            servicer_new.save()
                            servicer_list.append(_sayer)
                        if not shop:
                            if _sayer:
                                _q_servicer_list = Servicer.objects.all().filter(name=_sayer)
                                if _q_servicer_list.exists():
                                    shop = _q_servicer_list[0].shop.name
                        content = ''
                    else:
                        content = '%s%s' % (content, str(data_line))

            return report_dic


        else:
            error = "只支持文本文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_contents(self, request, shop, current_customer, dialog_contents):
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        _q_dialog = DialogJD.objects.filter(shop=shop, customer=current_customer)
        if _q_dialog.exists():
            dialog_order = _q_dialog[0]
            end_time = datetime.datetime.strptime(str(dialog_contents[-1][1]), '%Y-%m-%d %H:%M:%S')
            if dialog_order.end_time == end_time:
                report_dic['discard'] += 1
                return report_dic
            dialog_order.end_time = end_time
            dialog_order.min += 1
        else:
            dialog_order = DialogJD()
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
            _q_dialog_detial = DialogJDDetail.objects.filter(sayer=dialog_content[0],
                                                             time=datetime.datetime.strptime
                                                             (str(dialog_content[1]), '%Y-%m-%d %H:%M:%S'))
            if _q_dialog_detial.exists():
                report_dic['discard'] += 1
                continue
            dialog_detial = DialogJDDetail()
            dialog_detial.dialog = dialog_order
            dialog_detial.sayer = dialog_content[0]
            dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            dialog_detial.content = dialog_content[2]
            d_value = (dialog_detial.time - previous_time).seconds
            dialog_detial.interval = d_value
            previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
            if dialog_content[0] == current_customer:
                dialog_detial.d_status = 1
            else:
                dialog_detial.d_status = 0
                if re.match(r'^·客服.+', str(dialog_detial.content)):
                    dialog_detial.category = 1
                elif re.match(r'^·您好.+', str(dialog_detial.content)):
                    dialog_detial.category = 2
            try:
                dialog_detial.creator = self.request.user.username
                dialog_detial.save()
            except Exception as e:
                report_dic['error'].append(e)
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
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJDDetail.objects.none()
        queryset = DialogJDDetail.objects.filter(extract_tag=False, category=1).order_by("-id")
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
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
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
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DialogJDWords.objects.none()
        queryset = DialogJDWords.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = DialogJDWordsFilter(params)
        serializer = DialogJDWordsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DialogJDWordsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DialogJDWords.objects.filter(id__in=order_ids, order_status=1)
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
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DialogOW.objects.none()
        queryset = DialogOW.objects.filter(is_order="是", order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
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
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
            "是否建配件工单": "is_order",
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
                             "是否建配件工单", "购买店铺", "省市区", "出厂序列号", "详细地址", "补寄原因", "配件信息", "损坏部位",
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
            order_fields = ["call_id", "guest_entry_time", "call_start_time", "first_response_time",
                            "average_response_time", "queue_time", "call_duration", "ender", "call_status",
                            "primary_classification", "secondary_classification", "three_level_classification",
                            "four_level_classification", "five_level_classification", "servicer", "customer",
                            "satisfaction", "rounds", "source", "goods_type", "purchase_time",
                            "is_order", "shop", "area", "m_sn", "address", "order_category", "broken_part",
                            "description", "mobile", "receiver"]
            for field in order_fields:
                setattr(order, field, row[field])

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
                    dialog_detial.sayer = dialog_content[0]
                    dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
                    dialog_detial.content = dialog_content[2]
                    d_value = (dialog_detial.time - previous_time).seconds
                    dialog_detial.interval = d_value
                    previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
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
        "GET": ['woinvoice.view_invoice']
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
        params["order_status"] = 1
        f = DialogOWFilter(params)
        serializer = DialogOWSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
            "是否建配件工单": "is_order",
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
                             "是否建配件工单", "购买店铺", "省市区", "出厂序列号", "详细地址", "补寄原因", "配件信息", "损坏部位",
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
            order_fields = ["call_id", "guest_entry_time", "call_start_time", "first_response_time",
                            "average_response_time", "queue_time", "call_duration", "ender", "call_status",
                            "primary_classification", "secondary_classification", "three_level_classification",
                            "four_level_classification", "five_level_classification", "servicer", "customer",
                            "satisfaction", "rounds", "source", "goods_type", "purchase_time",
                            "is_order", "shop", "area", "m_sn", "address", "order_category", "broken_part",
                            "description", "mobile", "receiver"]
            for field in order_fields:
                setattr(order, field, row[field])

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
                    dialog_detial.sayer = dialog_content[0]
                    dialog_detial.time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
                    dialog_detial.content = dialog_content[2]
                    d_value = (dialog_detial.time - previous_time).seconds
                    dialog_detial.interval = d_value
                    previous_time = datetime.datetime.strptime(str(dialog_content[1]), '%Y-%m-%d %H:%M:%S')
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
        "GET": ['woinvoice.view_invoice']
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_invoice']
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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

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
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)
