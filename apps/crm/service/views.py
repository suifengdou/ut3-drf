import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np
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
from .models import OriMaintenance, Maintenance, MaintenanceSummary, FindAndFound
from .serializers import OriMaintenanceSerializer, MaintenanceSerializer, MaintenanceSummarySerializer, FindAndFoundSerializer
from .filters import OriMaintenanceFilter, MaintenanceFilter, MaintenanceSummaryFilter, FindAndFoundFilter
from apps.utils.geography.models import Province, City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.crm.customers.models import Customer
from apps.crm.order.models import OrderInfo


class OriMaintenanceBeforeViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_orimaintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.filter(towork_status=1).exclude(order_status="已完成").order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["towork_status"] = 1
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["towork_status"] = 1
        if all_select_tag:
            handle_list = OriMaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriMaintenance.objects.filter(id__in=order_ids, towork_status=1)
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
            check_list.update(mark_name=0)
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
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
            reject_list.update(towork_status=0)
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
            "保修单号": "order_id",
            "保修单状态": "order_status",
            "收发仓库": "warehouse",
            "处理登记人": "completer",
            "保修类型": "maintenance_type",
            "故障类型": "fault_type",
            "送修类型": "transport_type",
            "序列号": "machine_sn",
            "换新序列号": "new_machine_sn",
            "关联订单号": "send_order_id",
            "保修结束语": "appraisal",
            "关联店铺": "shop",
            "购买时间": "purchase_time",
            "创建时间": "ori_create_time",
            "创建人": "ori_creator",
            "审核时间": "handle_time",
            "审核人": "handler_name",
            "保修完成时间": "finish_time",
            "保修金额": "fee",
            "保修数量": "quantity",
            "最后修改时间": "last_handle_time",
            "客户网名": "buyer_nick",
            "寄件客户姓名": "sender_name",
            "寄件客户手机": "sender_mobile",
            "寄件客户省市县": "sender_area",
            "寄件客户地址": "sender_address",
            "收件物流公司": "send_logistics_company",
            "收件物流单号": "send_logistics_no",
            "收件备注": "send_memory",
            "寄回客户姓名": "return_name",
            "寄回客户手机": "return_mobile",
            "寄回省市区": "return_area",
            "寄回地址": "return_address",
            "寄件指定物流公司": "return_logistics_company",
            "寄件物流单号": "return_logistics_no",
            "寄件备注": "return_memory",
            "保修货品商家编码": "goods_id",
            "保修货品名称": "goods_name",
            "保修货品简称": "goods_abbreviation",
            "故障描述": "description",
            "是否在保修期内": "is_guarantee",
            "收费状态": "charge_status",
            "收费金额": "charge_amount",
            "收费说明": "charge_memory"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["保修单号", "保修单状态", "收发仓库", "处理登记人", "保修类型", "故障类型", "送修类型", "序列号",
                             "换新序列号", "关联订单号", "保修结束语", "关联店铺", "购买时间", "创建时间", "创建人", "审核时间",
                             "审核人", "保修完成时间", "保修金额", "保修数量", "最后修改时间", "客户网名", "寄件客户姓名",
                             "寄件客户手机", "寄件客户省市县", "寄件客户地址", "收件物流公司", "收件物流单号", "收件备注",
                             "寄回客户姓名", "寄回客户手机", "寄回省市区", "寄回地址", "寄件指定物流公司", "寄件物流单号",
                             "寄件备注", "保修货品商家编码", "保修货品名称", "保修货品简称", "故障描述", "是否在保修期内",
                             "收费状态", "收费金额", "收费说明"]

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
            _ret_verify_field = OriMaintenance.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)
            if len(df) > 1000:
                queryset = OriMaintenance.objects.filter(towork_status=1).exclude(order_status="已完成")
                queryset.update(process_tag=1)
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
        before_status = ["待审核", "逆向待推送", "逆向推送失败", "待筛单", "不可达", "待取件", "取件失败", "待入库"]
        working_status = ["待维修", "已换新-待打单", "待打印", "已打印"]
        near_provinces = ["浙江", "山东", "安徽", "福建", "河南", "湖北", "湖南", "江西", "江苏", "上海"]
        for row in resource:
            _q_repeat_order = OriMaintenance.objects.filter(order_id=row["order_id"])
            if _q_repeat_order.exists():
                order =_q_repeat_order[0]
                if order.order_status == "已完成" or order.towork_status > 1:
                    report_dic["discard"] += 1
                    continue
                else:
                    order.towork_status = 1
                    order.process_tag = 0
            else:
                order = OriMaintenance()
            for keyword in ["purchase_time", "ori_create_time", "handle_time", "finish_time", "last_handle_time"]:
                if row[keyword] == "0000-00-00 00:00:00":
                    row[keyword] = None

            order_fields = ["order_id", "order_status", "warehouse", "completer", "maintenance_type",
                            "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                            "appraisal", "shop", "purchase_time", "ori_create_time", "ori_creator", "handle_time",
                            "handler_name", "finish_time", "fee", "quantity",  "buyer_nick",
                            "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                            "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                            "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                            "goods_id", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                            "charge_status", "charge_amount", "charge_memory"]
            for field in order_fields:
                setattr(order, field, row[field])
            current_time = datetime.datetime.now()
            if order.order_status in before_status and order.handle_time:
                handle_time = datetime.datetime.strptime(order.handle_time, "%Y-%m-%d %H:%M:%S")
                calc_day = (current_time - handle_time).days
                province_key = order.sender_area[:2]
                if province_key in near_provinces:
                    if calc_day > 3:
                        order.process_tag = 3
                else:
                    if calc_day > 5:
                        order.process_tag = 3
            if order.order_status in working_status and not order.last_handle_time:
                order.last_handle_time = row["last_handle_time"]
            if order.last_handle_time:
                if isinstance(order.last_handle_time, str):
                    last_handle_time = datetime.datetime.strptime(order.last_handle_time, "%Y-%m-%d %H:%M:%S")
                else:
                    last_handle_time = order.last_handle_time
                calc_day = (current_time - last_handle_time).days
                if calc_day > 2:
                    order.process_tag = 4
            if order.order_status == '已取消':
                order.towork_status = 0
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["order_id"])
                report_dic["false"] += 1

        return report_dic


class OriMaintenanceSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_orimaintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.filter(towork_status=1, order_status="已完成").order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["towork_status"] = 1
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["towork_status"] = 1
        params["order_status"] = "已完成"
        if all_select_tag:
            handle_list = OriMaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriMaintenance.objects.filter(id__in=order_ids, towork_status=1)
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
            "discard": 0,
            "error": []
        }
        special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市', '石河子市', '阿拉尔市',
                        '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市', '琼中黎族苗族自治县', '琼海市',
                        '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县', '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县',
                        '白沙黎族自治县', '中山市', '东莞市']
        if n:
            jieba.load_userdict("apps/dfc/manualorder/addr_key_words.txt")
            for obj in check_list:
                if obj.warehouse != "苏州小狗维修仓":
                    n -= 1
                    data["discard"] += 1
                    obj.towork_status = 3
                    obj.save()
                    continue
                if obj.maintenance_type == "以旧换新":
                    n -= 1
                    data["discard"] += 1
                    obj.towork_status = 3
                    obj.save()
                    continue
                _q_repeat_order = Maintenance.objects.filter(ori_maintenance=obj)
                if _q_repeat_order.exists():
                    order = _q_repeat_order[0]
                    if order.order_status in [0, 1]:
                        order.order_status = 1
                    elif order.order_status == 3:
                        obj.towork_status = 2
                        obj.mistake_tag = 0
                        obj.process_tag = 1
                        obj.save()
                        continue
                    else:
                        data["error"].append("%s 递交到保修单错乱" % obj.id)
                        n -= 1
                        obj.mistake_tag = 7
                        obj.save()
                        continue
                else:
                    order = Maintenance()
                obj.sender_mobile = re.sub("[ !$%&\'()*+,-./:;<=>?，。?★、…【】《》？]", "", str(obj.sender_mobile))
                if not re.match("^1[3-9][0-9]{9}$", obj.sender_mobile):
                    if obj.process_tag != 5:
                        data["error"].append("%s 尝试修复数据" % obj.id)
                        n -= 1
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                else:
                    _q_customer = Customer.objects.filter(name=obj.sender_mobile)
                    if _q_customer.exists():
                        order.customer = _q_customer[0]
                    else:
                        customer = Customer()
                        customer.name = obj.sender_mobile
                        customer.save()
                        order.customer = customer
                if re.match("^\d+$", obj.goods_id):
                    _q_goods = Goods.objects.filter(goods_number=obj.goods_id[:3])
                    if _q_goods.exists():
                        order.goods_name = _q_goods[0]
                    else:
                        data["error"].append("%s 此序号整机未创建" % obj.goods_id[:3])
                        n -= 1
                        obj.mistake_tag = 5
                        obj.save()
                        continue
                else:
                    _q_goods = Goods.objects.filter(goods_id=obj.goods_id)
                    if _q_goods.exists():
                        order.goods_name = _q_goods[0]
                    else:
                        data["error"].append("%s 此型号整机未创建" % obj.goods_id[:3])
                        n -= 1
                        obj.mistake_tag = 5
                        obj.save()
                        continue
                obj.sender_area = str(obj.sender_area).strip().replace("  ", " ")
                area = str(obj.sender_area).split(" ")
                if len(area) == 3:
                    _q_province = Province.objects.filter(name__icontains=area[0][:2])
                    if _q_province.exists():
                        province = _q_province[0]
                        order.province = province
                    _q_city = City.objects.filter(name=area[1])
                    if _q_city.exists():
                        order.city = _q_city[0]
                        order.province = _q_city[0].province
                    else:
                        _q_city = City.objects.filter(name__icontains=area[1][:2])
                        if _q_city.exists():
                            order.city = _q_city[0]
                            order.province = _q_city[0].province
                        else:
                            if province:
                                _q_district = District.objects.filter(province=province, name=area[1])
                                if _q_district.exists():
                                    order.district = _q_district[0]
                                    order.city = _q_district[0].city
                            else:
                                data["error"].append("%s 二级市错误" % obj.id)
                                n -= 1
                                obj.mistake_tag = 2
                                obj.save()
                                continue
                    if not order.district and str(area[1]) not in special_city:
                        _q_district = District.objects.filter(name=area[2])
                        if _q_district.exists():
                            order.district = _q_district[0]
                        else:
                            try:
                                order.district = District.objects.filter(city=order.city, name="其他区")[0]
                            except Exception as e:
                                pass

                elif len(area) == 2:
                    _q_city = City.objects.filter(name=area[1])
                    if _q_city.exists():
                        order.city = _q_city[0]
                        order.province = _q_city[0].province
                    else:
                        _q_city = City.objects.filter(name=area[0])
                        if _q_city.exists():
                            order.city = _q_city[0]
                            order.province = _q_city[0].province
                        else:
                            data["error"].append("%s 二级市错误" % obj.id)
                            n -= 1
                            obj.mistake_tag = 2
                            obj.save()
                            continue
                elif len(area) == 1:
                    address = re.sub("[0-9!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(obj.sender_address))
                    seg_list = jieba.lcut(address)
                    num = 0
                    for words in seg_list:
                        num += 1
                        if not order.province_id:
                            _q_province = Province.objects.filter(name__contains=words[:2])
                            if _q_province.exists():
                                order.province = _q_province[0]

                        if not order.city_id:
                            _q_city = City.objects.filter(name__contains=words)
                            if len(_q_city) == 1:
                                if not _q_city.exists():
                                    _q_city_again = City.objects.filter(name__contains=words[:2])
                                    if _q_city_again.exists():
                                        order.city = _q_city_again[0]
                                        if num < 3 and not order.province_id:
                                            order.province = order.city.province
                                else:
                                    order.city = _q_city[0]
                                    if num < 3 and not order.province_id:
                                        order.province = order.city.province
                        if not order.district_id:
                            if not order.city_id:
                                if order.province_id:
                                    _q_district_direct = District.objects.filter(province=order.province,
                                                                                 name__contains=words)
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
                                    if order.province_id:
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
                    if not order.city_id:
                        data["error"].append("%s 地址无法提取省市区" % obj.id)
                        n -= 1
                        obj.mistake_tag = 3
                        obj.save()
                        continue

                    if order.province_id != order.city.province.id:
                        data["error"].append("%s 地址无法提取省市区" % obj.id)
                        n -= 1
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                    if address.find(str(order.province.name)[:2]) == -1 and address.find(
                            str(order.city.name)[:2]) == -1:
                        data["error"].append("%s 地址无法提取省市区" % obj.id)
                        n -= 1
                        obj.mistake_tag = 3
                        obj.save()
                else:
                    data["error"].append("%s寄件地区出错" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                if obj.shop == "小狗电器旗舰店":
                    obj.shop = "小狗吸尘器官方旗舰店"
                _q_shop = Shop.objects.filter(name=obj.shop)
                if _q_shop.exists():
                    order.shop = _q_shop[0]
                else:
                    data["error"].append("%sUT系统无此店铺" % obj.id)
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                finish_date = obj.finish_time.strftime("%Y-%m-%d")
                order.finish_date = datetime.datetime.strptime(finish_date, "%Y-%m-%d")
                order.finish_month = obj.finish_time.strftime("%Y-%m")
                order.finish_year = obj.finish_time.strftime("%Y")
                order.ori_maintenance = obj

                order_fields = ["order_id", "warehouse", "maintenance_type", "fault_type", "machine_sn", "appraisal",
                                "description", "buyer_nick", "sender_name", "sender_mobile", "is_guarantee",
                                "charge_status", "charge_amount", "charge_memory", "ori_creator", "ori_create_time",
                                "handler_name", "handle_time", "completer", "finish_time"]
                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))

                try:
                    order.creator = request.user.username
                    order.save()
                    data["successful"] += 1
                except Exception as e:
                    n -= 1
                    data['error'].append("%s 保存出错" % obj.order_id)
                    data["false"] += 1
                    continue

                obj.towork_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 1
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "discard": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.mistake_tag != 1:
                    n -= 1
                    data["discard"] += 1
                    continue
                obj.process_tag = 5
                if obj.send_order_id:
                    _q_orderinf = OrderInfo.objects.filter(trade_no=obj.send_order_id)
                    if _q_orderinf.exists():
                        orderinfo = _q_orderinf[0]
                        obj.sender_name = orderinfo.receiver_name
                        obj.sender_mobile = orderinfo.receiver_mobile
                        obj.sender_address = orderinfo.receiver_address
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
            "保修单号": "order_id",
            "保修单状态": "order_status",
            "收发仓库": "warehouse",
            "处理登记人": "completer",
            "保修类型": "maintenance_type",
            "故障类型": "fault_type",
            "送修类型": "transport_type",
            "序列号": "machine_sn",
            "换新序列号": "new_machine_sn",
            "关联订单号": "send_order_id",
            "保修结束语": "appraisal",
            "关联店铺": "shop",
            "购买时间": "purchase_time",
            "创建时间": "ori_create_time",
            "创建人": "ori_creator",
            "审核时间": "handle_time",
            "审核人": "handler_name",
            "保修完成时间": "finish_time",
            "保修金额": "fee",
            "保修数量": "quantity",
            "最后修改时间": "last_handle_time",
            "客户网名": "buyer_nick",
            "寄件客户姓名": "sender_name",
            "寄件客户手机": "sender_mobile",
            "寄件客户省市县": "sender_area",
            "寄件客户地址": "sender_address",
            "收件物流公司": "send_logistics_company",
            "收件物流单号": "send_logistics_no",
            "收件备注": "send_memory",
            "寄回客户姓名": "return_name",
            "寄回客户手机": "return_mobile",
            "寄回省市区": "return_area",
            "寄回地址": "return_address",
            "寄件指定物流公司": "return_logistics_company",
            "寄件物流单号": "return_logistics_no",
            "寄件备注": "return_memory",
            "保修货品商家编码": "goods_id",
            "保修货品名称": "goods_name",
            "保修货品简称": "goods_abbreviation",
            "故障描述": "description",
            "是否在保修期内": "is_guarantee",
            "收费状态": "charge_status",
            "收费金额": "charge_amount",
            "收费说明": "charge_memory"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["保修单号", "保修单状态", "收发仓库", "处理登记人", "保修类型", "故障类型", "送修类型", "序列号",
                             "换新序列号", "关联订单号", "保修结束语", "关联店铺", "购买时间", "创建时间", "创建人", "审核时间",
                             "审核人", "保修完成时间", "保修金额", "保修数量", "最后修改时间", "客户网名", "寄件客户姓名",
                             "寄件客户手机", "寄件客户省市县", "寄件客户地址", "收件物流公司", "收件物流单号", "收件备注",
                             "寄回客户姓名", "寄回客户手机", "寄回省市区", "寄回地址", "寄件指定物流公司", "寄件物流单号",
                             "寄件备注", "保修货品商家编码", "保修货品名称", "保修货品简称", "故障描述", "是否在保修期内",
                             "收费状态", "收费金额", "收费说明"]

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
            _ret_verify_field = OriMaintenance.verify_mandatory(columns_key)
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
            _q_repeat_order = OriMaintenance.objects.filter(order_id=row["order_id"])
            if _q_repeat_order.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["order_id"])
                continue
            for keyword in ["purchase_time", "ori_create_time", "handle_time", "finish_time", "last_handle_time"]:
                if row[keyword] == "0000-00-00 00:00:00":
                    row[keyword] = None
            order = OriMaintenance()
            order_fields = ["order_id", "order_status", "warehouse", "completer", "maintenance_type",
                            "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                            "appraisal", "shop", "purchase_time", "ori_create_time", "ori_creator", "handle_time",
                            "handler_name", "finish_time", "fee", "quantity", "last_handle_time", "buyer_nick",
                            "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                            "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                            "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                            "goods_id", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                            "charge_status", "charge_amount", "charge_memory"]
            for field in order_fields:
                setattr(order, field, row[field])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["order_id"])
                report_dic["false"] += 1

        return report_dic


class OriMaintenanceViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_orimaintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)


class MaintenanceSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=1)
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
            "tag_successful": 0,
            "error": []
        }
        if n:
            days_list_ori = list(check_list.order_by("finish_date").values_list("finish_date", flat=True).distinct())

            if days_list_ori:
                min_date = min(days_list_ori)
                max_date = max(days_list_ori) + datetime.timedelta(days=1)
                current_date = min_date

                max_date_exists = MaintenanceSummary.objects.all().aggregate(Max("finish_date"))["finish_date__max"]
                if max_date_exists:
                    if min_date <= max_date_exists:
                        if max_date < max_date_exists:
                            max_date = max_date_exists

            while current_date < max_date:
                    repeat_dic = {"successful": 0, "tag_successful": 0, "false": 0, "error": []}

                    # 当前天减去一天，作为前一天，作为前三十天的基准时间。
                    end_date = current_date - datetime.timedelta(days=1)
                    start_date = current_date - datetime.timedelta(days=31)
                    # 查询近三十天到所有单据，准备进行匹配查询。
                    maintenance_checked = Maintenance.objects.filter(finish_date__gte=start_date,
                                                                                 finish_date__lte=end_date)

                    # 创建二次维修率的表单对象，
                    verify_condition = MaintenanceSummary.objects.filter(finish_date=current_date)
                    current_update_orders = check_list.filter(finish_date=current_date)
                    if verify_condition.exists():
                        current_summary = verify_condition[0]
                        current_summary.order_count += current_update_orders.count()
                        try:
                            current_summary.save()
                            repeat_dic['error'].append("%s 更新了这个日期的当日保修单数量，之前保修单导入时有遗漏！" % current_date)
                        except Exception as e:
                            repeat_dic['error'].append(e)
                    else:
                        current_summary = MaintenanceSummary()
                        current_summary.finish_date = current_date
                        current_summary.order_count = current_update_orders.count()
                        current_summary.creator = request.user.username
                        try:
                            current_summary.save()
                        except Exception as e:
                            repeat_dic['error'].append(e)

                    # 首先生成统计表，然后更新累加统计表在每个循环。然后查询出二次维修，则检索二次维修当天统计表，进而更新二次维修数量。
                    # 当天的二次维修检查数量，是发现二次维修数量，而不是当天的二次维修数量，是客户在当天的不满意数量。
                    # 循环当前天的订单数据，根据当前天的sn查询出前三十天的二次维修问题。
                    for order in current_update_orders:
                        if not order.machine_sn or not re.match("^[0-9].+", str(order.machine_sn)):
                            try:
                                order.order_status = 3
                                order.save()
                                repeat_dic['successful'] += 1
                                continue
                            except Exception as e:
                                repeat_dic['error'].append(e)
                                repeat_dic['false'] += 1
                                continue
                        result_checked = maintenance_checked.filter(machine_sn=order.machine_sn, repeat_tag=0)
                        if result_checked.exists():

                            order.found_tag = True
                            order.order_status = 2
                            found_order = result_checked[0]
                            found_order.repeat_tag = 1
                            found_order.order_status = 2
                            find_found = FindAndFound()
                            find_found.find = order
                            find_found.found = found_order
                            find_found.creator = request.user.username
                            found_history_summary = MaintenanceSummary.objects.filter(finish_date=found_order.finish_date)[0]
                            found_history_summary.repeat_today += 1
                            current_summary.repeat_found += 1

                            try:
                                order.save()
                                found_order.save()
                                find_found.save()
                                current_summary.save()
                                found_history_summary.save()
                                repeat_dic['successful'] += 1
                                repeat_dic['tag_successful'] += 1
                            except Exception as e:
                                repeat_dic['error'].append(e)
                                repeat_dic['false'] += 1

                        else:
                            try:
                                order.order_status = 3
                                order.save()
                                repeat_dic['successful'] += 1
                            except Exception as e:
                                repeat_dic['error'].append(e)
                                repeat_dic['false'] += 1

                    # 对数据进行汇总，累加到repeat_dic_total的字典里面
                    data['successful'] += repeat_dic['successful']
                    data['false'] += repeat_dic['false']
                    data['tag_successful'] = repeat_dic['tag_successful']
                    if repeat_dic['error']:
                        data['error'].append(repeat_dic['error'])

                    current_date = current_date + datetime.timedelta(days=1)


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
                obj.ori_maintenance.towork_status = 1
                obj.ori_maintenance.save()
                obj.order_status = 0
                obj.save()
                data["successful"] += 1
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
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
            _ret_verify_field = Maintenance.verify_mandatory(columns_key)
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
            _q_calllog = Maintenance.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = Maintenance()
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


class MaintenanceJudgmentViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=2)
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
                if not obj.found_tag:
                    if obj.repeat_tag == 1:
                        data["error"].append("%s二次维修未操作不可以审核" % obj.id)
                        n -= 1
                        continue
                try:
                    obj.order_status = 3
                    obj.save()
                except Exception as e:
                    data["error"].append("%s保修单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.save()
                    continue
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
            _ret_verify_field = Maintenance.verify_mandatory(columns_key)
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
            _q_calllog = Maintenance.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = Maintenance()
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


class MaintenanceViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=3)
            else:
                handle_list = []
        return handle_list

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


class FindAndFoundViewset(viewsets.ModelViewSet):
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
    serializer_class = FindAndFoundSerializer
    filter_class = FindAndFoundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return FindAndFound.objects.none()
        queryset = FindAndFound.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = FindAndFoundFilter(params)
        serializer = FindAndFoundSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=3)
            else:
                handle_list = []
        return handle_list

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


class MaintenanceSummaryViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSummarySerializer
    filter_class = MaintenanceSummaryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return MaintenanceSummary.objects.none()
        queryset = MaintenanceSummary.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenanceSummaryFilter(params)
        serializer = MaintenanceSummarySerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = MaintenanceSummaryFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MaintenanceSummary.objects.filter(id__in=order_ids)
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
                current_data = Maintenance.objects.filter(finish_date=obj.finish_date)
                obj.repeat_found = current_data.filter(found_tag=True).count()
                obj.repeat_today = current_data.filter(repeat_tag__in=[1, 2, 3, 4]).count()
                obj.creator = request.user.username
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
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
            _ret_verify_field = MaintenanceSummary.verify_mandatory(columns_key)
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
            _q_calllog = MaintenanceSummary.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = MaintenanceSummary()
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


