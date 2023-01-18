import datetime, math, re
import pandas as pd
from decimal import Decimal
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import OriOrder, DecryptOrder, LogOriOrder, LogDecryptOrder
from .serializers import OriOrderSerializer, DecryptOrderSerializer

from .filters import OriOrderFilter, DecryptOrderFilter
from apps.dfc.manualorder.models import ManualOrder
from apps.dfc.batchtable.models import BatchTable
from apps.crm.customers.models import Customer
from apps.utils.geography.models import City
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.psi.outbound.models import Outbound
from apps.utils.logging.loggings import logging, getlogs
from ut3.settings import EXPORT_TOPLIMIT


class OriOrderStockOutSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.filter(order_status=1, category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["category"] = 1
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def export_src_tids(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["category"] = 1
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:200], many=True)
        return Response(serializer.data)


    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["category"] = 1
        if all_select_tag:
            handle_list = OriOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrder.objects.filter(id__in=order_ids, order_status=1, category=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
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
                if all([obj.receiver, obj.mobile, obj.address]):
                    obj.process_tag = 1
                    obj.mistake_tag = 0
                    obj.save()
                    logging(obj, user, LogOriOrder, "订单解密")
                    continue
                if obj.process_tag not in [0, 3]:
                    obj.mistake_tag = 1
                    data["error"].append("%s 非待解密订单无需解密" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                if obj.print_remark:
                    mobiles = re.findall('\d{11}', str(obj.print_remark))
                    result_mobiles = []
                    if mobiles:
                        for mobile in mobiles:
                            if re.match('^1[3-9]\d{9}', str(mobile)):
                                result_mobiles.append(mobile)
                    if result_mobiles:
                        customer_info = re.split('\s', str(obj.print_remark))
                        if len(result_mobiles) == 1:
                            mobile_index = customer_info.index(str(result_mobiles[0]))
                        elif len(result_mobiles) == 2:
                            mobile_index = customer_info.index(str(result_mobiles[1]), 1)
                        if mobile_index:
                            obj.receiver = customer_info[mobile_index - 1]
                            obj.mobile = result_mobiles[0]
                            obj.address = ''.join(customer_info[mobile_index + 1:])
                            obj.process_tag = 1
                            obj.mistake_tag = 0
                            obj.save()
                            logging(obj, user, LogOriOrder, "订单解密")
                            continue
                if re.match('^SS', str(obj.src_tids)) or re.match('^\d{8}[A-Z]{2}', str(obj.src_tids)):
                    _q_order = ManualOrder.objects.filter(erp_order_id=obj.src_tids)
                    if _q_order.exists():
                        order = _q_order[0]
                        _check_mobile = re.findall('(\d{11}-\d{4})', str(order.address))
                        if not _check_mobile:
                            obj.receiver = order.receiver
                            obj.mobile = order.mobile
                            obj.address = order.address
                            obj.process_tag = 1
                            obj.mistake_tag = 0
                            obj.save()
                            logging(obj, user, LogOriOrder, "订单解密")
                            continue
                _q_decrypt_order = DecryptOrder.objects.filter(src_tids=obj.src_tids)
                if _q_decrypt_order.exists():
                    order = _q_decrypt_order[0]
                    if order.order_status == 2:
                        obj.receiver = order.receiver
                        obj.mobile = order.mobile
                        obj.address = order.address
                        obj.process_tag = 1
                        obj.mistake_tag = 0
                        obj.save()
                        logging(obj, user, LogOriOrder, "订单解密")
                        continue

                else:
                    n -= 1
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
                if not obj.mobile:
                    obj.mistake_tag = 1
                    data["error"].append("%s 先校正订单" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_customer = Customer.objects.filter(name=obj.mobile)
                if _q_customer.exists():
                    customer = _q_customer[0]
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()
                order = OriOrder()
                attr_fields = ['buyer_nick', 'trade_no', 'name', 'address', 'mobile', "goods_name", "shop_name",
                               'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                               'src_tids', 'num', 'price', 'share_amount', 'spec_code', 'order_category',
                               'logistics_name', 'warehouse_name', 'print_remark']
                for keyword in attr_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.customer = customer
                order.ori_order = obj
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    order.warehouse_name = _q_warehouse[0]
                else:
                    obj.mistake_tag = 5
                    data["error"].append("%s UT中无此仓库，先添加仓库" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop_name)
                if _q_shop.exists():
                    order.shop_name = _q_shop[0]
                else:
                    obj.mistake_tag = 4
                    data["error"].append("%s UT中无此店铺，先添加店铺" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_goods = Goods.objects.filter(goods_id=obj.spec_code)
                if _q_goods.exists():
                    order.goods_name = _q_goods[0]
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s UT中无此货品，先添加货品" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                area_list = str(obj.receiver_area).split(" ")
                for city_key in area_list:
                    _q_city = City.objects.filter(name=city_key)
                    if _q_city.exists():
                        order.city = _q_city[0]
                        break
                try:
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data['error'].append("%s 保存出错" % obj.trade_no)
                    data["false"] += 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '子单原始单号': 'src_tids',
            '原始子订单号': 'sub_src_tids',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '发货时间': 'deliver_time',
            '付款时间': 'pay_time',
            '收货地区': 'area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '打印备注': 'print_remark',
            '货品数量': 'quantity',
            '实际重量': 'actual_weight',
            '预估重量': 'weight',
            '货品成交价': 'price',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
            '出库单状态': 'erp_order_status',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '发货时间', '付款时间', '收货地区',
                             '物流单号', '买家留言', '客服备注', '子单原始单号', '货品数量', '货品成交价', '货品名称', '预估重量',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型', '原始子订单号', '打印备注', '实际重量', '出库单状态']

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误: %s" % e)
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])


            VERIFY_FIELD = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'erp_order_status',
                            'deliver_time', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'quantity', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark', 'actual_weight']
            for i in VERIFY_FIELD:
                if i not in columns_key:
                    report_dic["error"].append("必要字段不全或者错误，缺失字段：%s" % str(i))
                    return report_dic

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
        user = request.user
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            if row['trade_no'] == '合计:':
                continue
            if "0000-00-00" in str(row['pay_time']):
                row['pay_time'] = row['deliver_time']
            if '*' in str(row['mobile']):
                row['mobile'] = None
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'erp_order_status',
                            'deliver_time', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'quantity', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark', 'actual_weight']
            _q_order = OriOrder.objects.filter(trade_no=row["trade_no"], sub_src_tids=row["sub_src_tids"], spec_code=row["spec_code"])
            if _q_order.exists():
                order = _q_order[0]
                if order.category == 1:
                    report_dic["error"].append("%s 已存在此订单" % row["trade_no"])
                    report_dic["false"] += 1
                    continue
                else:
                    order.category = 1
            else:
                order = OriOrder()
            for field in order_fields:
                value = str(row[field])
                if not value in ["NaN", "nan"]:
                    setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            order.amount = (Decimal(str(order.price)) * Decimal(str(order.quantity))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            if all([order.receiver, order.mobile, order.address]):
                order.process_tag = 1
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
                logging(order, user, LogOriOrder, "导入发货明细")
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1

        return report_dic


class OriOrderStockOutCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.filter(order_status=2, category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["category"] = 1
        params["order_status"] = 2
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["category"] = 1
        params["order_status"] = 2
        if all_select_tag:
            handle_list = OriOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrder.objects.filter(id__in=order_ids, order_status=2, category=1)
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
                fields = ["buyer_nick", "receiver_name", "address", "mobile"]
                m_fields = ["nickname", "receiver", "address", "mobile"]
                if order.src_tids:
                    _q_bms_order = OriOrder.objects.filter(src_tids=order.src_tids)
                    if _q_bms_order.exists():
                        bms_order = _q_bms_order[0]
                        for field in fields:
                            setattr(order, field, getattr(bms_order, field, None))
                    else:
                        _q_manual_order = ManualOrder.objects.filter(erp_order_id=order.src_tids)
                        if _q_manual_order.exists():
                            manual_order = _q_manual_order[0]
                            for index in range(len(fields)):
                                setattr(order, fields[index], getattr(manual_order, m_fields[index], None))
                        else:
                            _q_batch_table = BatchTable.objects.filter()
                            if _q_batch_table.exists():
                                batch_table = _q_batch_table[0]
                                for index in range(len(fields)):
                                    setattr(order, fields[index], getattr(batch_table, m_fields[index], None))
                            else:
                                n -= 1
                else:
                    n -= 1
                order.process_tag = 1
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
                if not obj.mobile:
                    obj.mistake_tag = 1
                    data["error"].append("%s 先校正订单" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_customer = Customer.objects.filter(name=obj.mobile)
                if _q_customer.exists():
                    customer = _q_customer[0]
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()
                order = OriOrder()
                attr_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', "goods_name", "shop_name",
                               'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                               'src_tids', 'num', 'price', 'share_amount', 'spec_code', 'order_category',
                               'logistics_name', 'warehouse_name', 'print_remark']
                for keyword in attr_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.customer = customer
                order.ori_order = obj
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    order.warehouse_name = _q_warehouse[0]
                else:
                    obj.mistake_tag = 5
                    data["error"].append("%s UT中无此仓库，先添加仓库" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop_name)
                if _q_shop.exists():
                    order.shop_name = _q_shop[0]
                else:
                    obj.mistake_tag = 4
                    data["error"].append("%s UT中无此店铺，先添加店铺" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_goods = Goods.objects.filter(goods_id=obj.spec_code)
                if _q_goods.exists():
                    order.goods_name = _q_goods[0]
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s UT中无此货品，先添加货品" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                area_list = str(obj.receiver_area).split(" ")
                for city_key in area_list:
                    _q_city = City.objects.filter(name=city_key)
                    if _q_city.exists():
                        order.city = _q_city[0]
                        break
                try:
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data['error'].append("%s 保存出错" % obj.trade_no)
                    data["false"] += 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '子单原始单号': 'src_tids',
            '子单原始子订单号': 'sub_src_tids',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '发货时间': 'deliver_time',
            '付款时间': 'pay_time',
            '收货地区': 'area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '打印备注': 'print_remark',
            '下单数量': 'num',
            '实发数量': 'quantity',
            '预估重量': 'weight',
            '成交价': 'price',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '发货时间', '付款时间', '收货地区',
                             '物流单号', '买家留言', '客服备注', '子单原始单号', '下单数量', '成交价', '货品名称', '预估重量',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型', '子单原始子单号', '打印备注', '实发数量']

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
            _ret_verify_field = OriOrder.verify_mandatory(columns_key)
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
            if row['trade_no'] == '合计:':
                continue
            if "0000-00-00" in str(row['pay_time']):
                row['pay_time'] = row['deliver_time']
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'quantity',
                            'deliver_time', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'num', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark', ]
            _q_order = OriOrder.objects.filter(trade_no=row["trade_no"], sub_src_tids=row["sub_src_tids"], spec_code=row["spec_code"])
            if _q_order.exists():
                report_dic["error"].append("%s 已存在此订单" % row["trade_no"])
                report_dic["false"] += 1
                continue
            else:
                order = OriOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1

        return report_dic


class OriOrderDetailsSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.filter(order_status=1, category=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["category"] = 2
        params["order_status"] = 1
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def export_src_tids(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["category"] = 2
        params["order_status"] = 1
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:200], many=True)
        return Response(serializer.data)


    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["category"] = 2
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrder.objects.filter(id__in=order_ids, order_status=1, category=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
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
                if all([obj.receiver, obj.mobile, obj.address]):
                    obj.process_tag = 1
                    obj.mistake_tag = 0
                    obj.save()
                    logging(obj, user, LogOriOrder, "订单解密")
                    continue
                if obj.process_tag not in [0, 3]:
                    obj.mistake_tag = 1
                    data["error"].append("%s 非待解密订单无需解密" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                if obj.print_remark:
                    mobiles = re.findall('\d{11}', str(obj.print_remark))
                    result_mobiles = []
                    if mobiles:
                        for mobile in mobiles:
                            if re.match('^1[3-9]\d{9}', str(mobile)):
                                result_mobiles.append(mobile)
                    if result_mobiles:
                        customer_info = re.split('\s', str(obj.print_remark))
                        if len(result_mobiles) == 1:
                            mobile_index = customer_info.index(str(result_mobiles[0]))
                        elif len(result_mobiles) == 2:
                            mobile_index = customer_info.index(str(result_mobiles[1]), 1)
                        if mobile_index:
                            obj.receiver = customer_info[mobile_index - 1]
                            obj.mobile = result_mobiles[0]
                            obj.address = ''.join(customer_info[mobile_index + 1:])
                            obj.process_tag = 1
                            obj.mistake_tag = 0
                            obj.save()
                            logging(obj, user, LogOriOrder, "订单解密")
                            continue
                if re.match('^SS', str(obj.src_tids)) or re.match('^\d{8}[A-Z]{2}', str(obj.src_tids)):
                    _q_order = ManualOrder.objects.filter(erp_order_id=obj.src_tids)
                    if _q_order.exists():
                        order = _q_order[0]
                        _check_mobile = re.findall('(\d{11}-\d{4})', str(order.address))
                        if not _check_mobile:
                            obj.receiver = order.receiver
                            obj.mobile = order.mobile
                            obj.address = order.address
                            obj.process_tag = 1
                            obj.mistake_tag = 0
                            obj.save()
                            logging(obj, user, LogOriOrder, "订单解密")
                            continue
                _q_decrypt_order = DecryptOrder.objects.filter(src_tids=obj.src_tids)
                if _q_decrypt_order.exists():
                    order = _q_decrypt_order[0]
                    if order.order_status == 2:
                        obj.receiver = order.receiver
                        obj.mobile = order.mobile
                        obj.address = order.address
                        obj.process_tag = 1
                        obj.mistake_tag = 0
                        obj.save()
                        logging(obj, user, LogOriOrder, "订单解密")
                        continue
                else:
                    n -= 1
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
                if not obj.mobile:
                    obj.mistake_tag = 1
                    data["error"].append("%s 先校正订单" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_customer = Customer.objects.filter(name=obj.mobile)
                if _q_customer.exists():
                    customer = _q_customer[0]
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()
                order = OriOrder()
                attr_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', "goods_name", "shop_name",
                               'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                               'src_tids', 'num', 'price', 'share_amount', 'spec_code', 'order_category',
                               'logistics_name', 'warehouse_name', 'print_remark']
                for keyword in attr_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.customer = customer
                order.ori_order = obj
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    order.warehouse_name = _q_warehouse[0]
                else:
                    obj.mistake_tag = 5
                    data["error"].append("%s UT中无此仓库，先添加仓库" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop_name)
                if _q_shop.exists():
                    order.shop_name = _q_shop[0]
                else:
                    obj.mistake_tag = 4
                    data["error"].append("%s UT中无此店铺，先添加店铺" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_goods = Goods.objects.filter(goods_id=obj.spec_code)
                if _q_goods.exists():
                    order.goods_name = _q_goods[0]
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s UT中无此货品，先添加货品" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                area_list = str(obj.receiver_area).split(" ")
                for city_key in area_list:
                    _q_city = City.objects.filter(name=city_key)
                    if _q_city.exists():
                        order.city = _q_city[0]
                        break
                try:
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data['error'].append("%s 保存出错" % obj.trade_no)
                    data["false"] += 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '子单原始单号': 'src_tids',
            '子单原始子单号': 'sub_src_tids',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '付款时间': 'pay_time',
            '收货地区': 'area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '打印备注': 'print_remark',
            '下单数量': 'num',
            '实发数量': 'quantity',
            '预估重量': 'weight',
            '成交价': 'price',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
            '标记名称': 'sign',
            '订单状态': 'erp_order_status',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '付款时间', '收货地区', '标记名称',
                             '物流单号', '买家留言', '客服备注', '子单原始单号', '下单数量', '成交价', '货品名称', '预估重量',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型', '子单原始子单号', '打印备注', '实发数量', '订单状态']

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

            VERIFY_FIELD = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'erp_order_status',
                            'sign', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'quantity', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark']
            for i in VERIFY_FIELD:
                if i not in columns_key:
                    report_dic["error"].append("必要字段不全或者错误，缺失字段：%s" % str(i))
                    return report_dic


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
        user = request.user
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            if row['trade_no'] == '合计:':
                continue
            if row['erp_order_status'] != '待客审':
                report_dic["error"].append("%s 订单明细需要待客审" % row["trade_no"])
                report_dic["false"] += 1
                continue
            if "0000-00-00" in str(row['pay_time']):
                report_dic["error"].append("%s 此订单付款时间错误" % row["trade_no"])
                report_dic["false"] += 1
                continue
            if '*' in str(row['mobile']):
                row['mobile'] = None
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids',
                            'erp_order_status', 'sign', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'quantity', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark']

            _q_order = OriOrder.objects.filter(trade_no=row["trade_no"], sub_src_tids=row["sub_src_tids"], spec_code=row["spec_code"])
            if _q_order.exists():
                order = _q_order[0]
                if order.category == 1:
                    report_dic["error"].append("%s 此订单已存在出库，此表存在错误" % row["trade_no"])
                    report_dic["false"] += 1
                    continue
            else:
                order = OriOrder()
                order.category = 2
            for field in order_fields:
                value = str(row[field])
                if not value in ["NaN", "nan"]:
                    setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            order.amount = (Decimal(str(order.price)) * Decimal(str(order.quantity))).quantize(Decimal('0.00'),
                                                                                               rounding=ROUND_HALF_UP)
            if all([order.receiver, order.mobile, order.address]):
                order.process_tag = 1
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
                logging(order, user, LogOriOrder, "导入订单明细")
            except Exception as e:
                report_dic['error'].append("%s 保存出错：%s" % (row["trade_no"], e))
                report_dic["false"] += 1
        return report_dic


class OriOrderDetailsCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.filter(order_status=2, category=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["category"] = 2
        params["order_status"] = 2
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["category"] = 2
        params["order_status"] = 2
        if all_select_tag:
            handle_list = OriOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrder.objects.filter(id__in=order_ids, order_status=1, category=2)
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
                fields = ["buyer_nick", "receiver_name", "address", "mobile"]
                m_fields = ["nickname", "receiver", "address", "mobile"]
                if order.src_tids:
                    _q_bms_order = OriOrder.objects.filter(src_tids=order.src_tids)
                    if _q_bms_order.exists():
                        bms_order = _q_bms_order[0]
                        for field in fields:
                            setattr(order, field, getattr(bms_order, field, None))
                    else:
                        _q_manual_order = ManualOrder.objects.filter(erp_order_id=order.src_tids)
                        if _q_manual_order.exists():
                            manual_order = _q_manual_order[0]
                            for index in range(len(fields)):
                                setattr(order, fields[index], getattr(manual_order, m_fields[index], None))
                        else:
                            _q_batch_table = BatchTable.objects.filter()
                            if _q_batch_table.exists():
                                batch_table = _q_batch_table[0]
                                for index in range(len(fields)):
                                    setattr(order, fields[index], getattr(batch_table, m_fields[index], None))
                            else:
                                n -= 1
                else:
                    n -= 1
                order.process_tag = 1
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
                if not obj.mobile:
                    obj.mistake_tag = 1
                    data["error"].append("%s 先校正订单" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_customer = Customer.objects.filter(name=obj.mobile)
                if _q_customer.exists():
                    customer = _q_customer[0]
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()
                order = OriOrder()
                attr_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', "goods_name", "shop_name",
                               'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                               'src_tids', 'num', 'price', 'share_amount', 'spec_code', 'order_category',
                               'logistics_name', 'warehouse_name', 'print_remark']
                for keyword in attr_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.customer = customer
                order.ori_order = obj
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    order.warehouse_name = _q_warehouse[0]
                else:
                    obj.mistake_tag = 5
                    data["error"].append("%s UT中无此仓库，先添加仓库" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop_name)
                if _q_shop.exists():
                    order.shop_name = _q_shop[0]
                else:
                    obj.mistake_tag = 4
                    data["error"].append("%s UT中无此店铺，先添加店铺" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_goods = Goods.objects.filter(goods_id=obj.spec_code)
                if _q_goods.exists():
                    order.goods_name = _q_goods[0]
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s UT中无此货品，先添加货品" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                area_list = str(obj.receiver_area).split(" ")
                for city_key in area_list:
                    _q_city = City.objects.filter(name=city_key)
                    if _q_city.exists():
                        order.city = _q_city[0]
                        break
                try:
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data['error'].append("%s 保存出错" % obj.trade_no)
                    data["false"] += 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '子单原始单号': 'src_tids',
            '子单原始子订单号': 'sub_src_tids',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '发货时间': 'deliver_time',
            '付款时间': 'pay_time',
            '收货地区': 'area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '打印备注': 'print_remark',
            '下单数量': 'num',
            '实发数量': 'quantity',
            '预估重量': 'weight',
            '成交价': 'price',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '发货时间', '付款时间', '收货地区',
                             '物流单号', '买家留言', '客服备注', '子单原始单号', '下单数量', '成交价', '货品名称', '预估重量',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型', '子单原始子单号', '打印备注', '实发数量']

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
            _ret_verify_field = OriOrder.verify_mandatory(columns_key)
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
            if row['trade_no'] == '合计:':
                continue
            if "0000-00-00" in str(row['pay_time']):
                row['pay_time'] = row['deliver_time']
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'quantity',
                            'deliver_time', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'num', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark', ]
            _q_order = OriOrder.objects.filter(trade_no=row["trade_no"], sub_src_tids=row["sub_src_tids"], spec_code=row["spec_code"])
            if _q_order.exists():
                report_dic["error"].append("%s 已存在此订单" % row["trade_no"])
                report_dic["false"] += 1
                continue
            else:
                order = OriOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1

        return report_dic


class OriOrderDetailsRefundViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.filter(order_status=2, category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrder.objects.filter(id__in=order_ids, order_status=1)
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
                fields = ["buyer_nick", "receiver_name", "address", "mobile"]
                m_fields = ["nickname", "receiver", "address", "mobile"]
                if order.src_tids:
                    _q_bms_order = OriOrder.objects.filter(src_tids=order.src_tids)
                    if _q_bms_order.exists():
                        bms_order = _q_bms_order[0]
                        for field in fields:
                            setattr(order, field, getattr(bms_order, field, None))
                    else:
                        _q_manual_order = ManualOrder.objects.filter(erp_order_id=order.src_tids)
                        if _q_manual_order.exists():
                            manual_order = _q_manual_order[0]
                            for index in range(len(fields)):
                                setattr(order, fields[index], getattr(manual_order, m_fields[index], None))
                        else:
                            _q_batch_table = BatchTable.objects.filter()
                            if _q_batch_table.exists():
                                batch_table = _q_batch_table[0]
                                for index in range(len(fields)):
                                    setattr(order, fields[index], getattr(batch_table, m_fields[index], None))
                            else:
                                n -= 1
                else:
                    n -= 1
                order.process_tag = 1
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
                if not obj.mobile:
                    obj.mistake_tag = 1
                    data["error"].append("%s 先校正订单" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_customer = Customer.objects.filter(name=obj.mobile)
                if _q_customer.exists():
                    customer = _q_customer[0]
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()
                order = OriOrder()
                attr_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', "goods_name", "shop_name",
                               'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                               'src_tids', 'num', 'price', 'share_amount', 'spec_code', 'order_category',
                               'logistics_name', 'warehouse_name', 'print_remark']
                for keyword in attr_fields:
                    setattr(order, keyword, getattr(obj, keyword, None))
                order.customer = customer
                order.ori_order = obj
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    order.warehouse_name = _q_warehouse[0]
                else:
                    obj.mistake_tag = 5
                    data["error"].append("%s UT中无此仓库，先添加仓库" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_shop = Shop.objects.filter(name=obj.shop_name)
                if _q_shop.exists():
                    order.shop_name = _q_shop[0]
                else:
                    obj.mistake_tag = 4
                    data["error"].append("%s UT中无此店铺，先添加店铺" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                _q_goods = Goods.objects.filter(goods_id=obj.spec_code)
                if _q_goods.exists():
                    order.goods_name = _q_goods[0]
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s UT中无此货品，先添加货品" % obj.trade_no)
                    obj.save()
                    n -= 1
                    continue
                area_list = str(obj.receiver_area).split(" ")
                for city_key in area_list:
                    _q_city = City.objects.filter(name=city_key)
                    if _q_city.exists():
                        order.city = _q_city[0]
                        break
                try:
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    data['error'].append("%s 保存出错" % obj.trade_no)
                    data["false"] += 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '子单原始单号': 'src_tids',
            '子单原始子订单号': 'sub_src_tids',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '发货时间': 'deliver_time',
            '付款时间': 'pay_time',
            '收货地区': 'area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '打印备注': 'print_remark',
            '下单数量': 'num',
            '实发数量': 'quantity',
            '预估重量': 'weight',
            '成交价': 'price',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '发货时间', '付款时间', '收货地区',
                             '物流单号', '买家留言', '客服备注', '子单原始单号', '下单数量', '成交价', '货品名称', '预估重量',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型', '子单原始子单号', '打印备注', '实发数量']

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
            _ret_verify_field = OriOrder.verify_mandatory(columns_key)
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
            if row['trade_no'] == '合计:':
                continue
            if "0000-00-00" in str(row['pay_time']):
                row['pay_time'] = row['deliver_time']
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids', 'quantity',
                            'deliver_time', 'pay_time', 'area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'num', 'price', 'goods_name', 'spec_code', 'order_category', 'weight',
                            'shop_name', 'logistics_name', 'warehouse_name', 'print_remark', ]
            _q_order = OriOrder.objects.filter(trade_no=row["trade_no"], sub_src_tids=row["sub_src_tids"], spec_code=row["spec_code"])
            if _q_order.exists():
                report_dic["error"].append("%s 已存在此订单" % row["trade_no"])
                report_dic["false"] += 1
                continue
            else:
                order = OriOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1

        return report_dic


class OriOrderManageViewset(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = OriOrderSerializer
    filter_class = OriOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrder.objects.none()
        queryset = OriOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriOrderFilter(params)
        serializer = OriOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = OriOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogOriOrder)
        return Response(ret)


class DecryptOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DecryptOrderSerializer
    filter_class = DecryptOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_orderinfo']
    }

    def get_queryset(self):
        if not self.request:
            return DecryptOrder.objects.none()
        queryset = DecryptOrder.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = DecryptOrderFilter(params)
        serializer = DecryptOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DecryptOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DecryptOrder.objects.filter(id__in=order_ids, order_status=1)
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
                if obj.warehouse_name.order_status:
                    _q_repeat_order = Outbound.objects.filter(ori_order_id=obj)
                    if _q_repeat_order.exists():
                        order = _q_repeat_order[0]
                        if order.order_status == 0:
                            order.order_status = 1
                        else:
                            obj.mistake_tag = 1
                            data["error"].append("%s 不可重复递交订单" % obj.trade_no)
                            obj.save()
                            n -= 1
                            continue
                    else:
                        order = Outbound()
                    from_fields = ["warehouse_name", "shop_name", "spec_code", "goods_name", "num", "deliver_time"]
                    attr_fields = ["warehouse", "shop", "goods_id", "goods_name", "quantity", "deliver_time"]
                    for index in range(len(attr_fields)):
                        setattr(order, attr_fields[index], getattr(obj, from_fields[index], None))
                    order.ob_order_id = "OB" + str(obj.trade_no)
                    order.ori_order_id = obj
                    try:
                        order.creator = request.user.username
                        order.save()
                    except Exception as e:
                        obj.mistake_tag = 2
                        data["error"].append("%s 保存出库单出错" % obj.trade_no)
                        obj.save()
                        n -= 1
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '收件人': 'receiver',
            '收货地址': 'address',
            '收件人手机': 'mobile',
            '发货时间': 'deliver_time',
            '付款时间': 'pay_time',
            '收货地区': 'receiver_area',
            '物流单号': 'logistics_no',
            '买家留言': 'buyer_message',
            '客服备注': 'cs_remark',
            '原始单号': 'src_tids',
            '货品数量': 'num',
            '货品成交价': 'price',
            '货品成交总价': 'share_amount',
            '货品名称': 'goods_name',
            '商家编码': 'spec_code',
            '店铺': 'shop_name',
            '物流公司': 'logistics_name',
            '仓库': 'warehouse_name',
            '订单类型': 'order_category',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['客户网名', '订单编号', '收件人', '收货地址', '收件人手机', '发货时间', '付款时间', '收货地区',
                             '物流单号', '买家留言', '客服备注', '原始单号', '货品数量', '货品成交价', '货品成交总价', '货品名称',
                             '商家编码', '店铺', '物流公司', '仓库', '订单类型']

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
            _ret_verify_field = OriOrder.verify_mandatory(columns_key)
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
            if row['trade_no'] == '合计:':
                continue
            if "0000-00-00" in str(row['pay_time']):
                row['pay_time'] = row['deliver_time']
            order_fields = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile',
                            'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'num', 'price', 'share_amount', 'goods_name', 'spec_code', 'order_category',
                            'shop_name', 'logistics_name', 'warehouse_name']
            order = OriOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            if not order.src_tids:
                order.src_tids = order.trade_no
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1

        return report_dic


class DecryptOrderManageViewset(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = DecryptOrderSerializer
    filter_class = DecryptOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_orderinfo']
    }

    def get_queryset(self):
        if not self.request:
            return DecryptOrder.objects.none()
        queryset = DecryptOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DecryptOrderFilter(params)
        serializer = DecryptOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


















