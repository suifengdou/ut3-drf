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


