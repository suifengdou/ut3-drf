import datetime, math
import pandas as pd
from decimal import Decimal
import numpy as np
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
from .models import OriOrderInfo, OrderInfo, BMSOrderInfo
from .serializers import OriOrderInfoSerializer, OrderInfoSerializer, BMSOrderInfoSerializer
from .filters import OriOrderInfoFilter, BMSOrderInfoFilter



class OriOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriOrderInfoSerializer
    filter_class = OriOrderInfoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrderInfo.objects.none()
        queryset = OriOrderInfo.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = OriOrderInfoFilter(params)
        serializer = OriOrderInfoSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = OriOrderInfoFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriOrderInfo.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
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
            for order in check_list:
                if order.is_customer_post:
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

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
            for order in check_list:
                if order.is_customer_post:
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
            '客户网名': 'buyer_nick',
            '订单编号': 'trade_no',
            '收件人': 'receiver_name',
            '收货地址': 'receiver_address',
            '收件人手机': 'receiver_mobile',
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
            _ret_verify_field = OriOrderInfo.verify_mandatory(columns_key)
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
            order_fields = ['buyer_nick', 'trade_no', 'receiver_name', 'receiver_address', 'receiver_mobile',
                            'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                            'src_tids', 'num', 'price', 'share_amount', 'goods_name', 'spec_code', 'order_category',
                            'shop_name', 'logistics_name', 'warehouse_name']
            order = OriOrderInfo()
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
    serializer_class = OriOrderInfoSerializer
    filter_class = OriOrderInfoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrderInfo.objects.none()
        queryset = OriOrderInfo.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriOrderInfoFilter(params)
        serializer = OriOrderInfoSerializer(f.qs, many=True)
        return Response(serializer.data)


class BMSOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = BMSOrderInfoSerializer
    filter_class = BMSOrderInfoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return BMSOrderInfo.objects.none()
        queryset = BMSOrderInfo.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = BMSOrderInfoFilter(params)
        serializer = BMSOrderInfoSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = BMSOrderInfoFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BMSOrderInfo.objects.filter(id__in=order_ids, order_status=1)
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
            for order in check_list:
                if order.is_customer_post:
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
            "店铺名称": "shop_name",
            "仓库名称": "warehouse_name",
            "支付时间": "pay_time",
            "订单类型": "order_category",
            "状态": "ori_order_status",
            "交易订单号": "src_tids",
            "仓库订单号": "trade_no",
            "快递公司": "logistics_name",
            "运单号": "logistics_no",
            "买家昵称": "buyer_nick",
            "收货人姓名": "receiver_name",
            "省": "province",
            "市": "city",
            "区": "district",
            "街道": "street",
            "收货人地址": "receiver_address",
            "手机": "receiver_mobile",
            "卖家备注": "cs_remark",
            "退款": "refund_tag",
            "订货数量": "order_num",
            "商品小计": "share_amount",
            "商品编码": "spec_code",
            "商品名称": "goods_name",
            "商品重量(克)": "goods_weight",
            "分销商店铺名称": "dealer_name",
            "分销订单号": "dealer_order_id",
            "实发数量": "num",
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["店铺名称", "仓库名称", "支付时间", "订单类型", "状态", "交易订单号", "仓库订单号",
                             "快递公司", "运单号", "买家昵称", "收货人姓名", "省", "市", "区", "街道", "收货人地址",
                             "手机", "卖家备注", "退款", "订货数量", "商品小计", "商品编码", "商品名称", "商品重量(克)",
                             "分销商店铺名称", "分销订单号", "实发数量"]

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
            _ret_verify_field = BMSOrderInfo.verify_mandatory(columns_key)
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
            order_fields = ["shop_name", "warehouse_name", "pay_time", "order_category", "ori_order_status",
                            "src_tids", "trade_no", "logistics_name", "logistics_no", "buyer_nick",
                            "receiver_name", "province", "city", "district", "street", "receiver_address",
                            "receiver_mobile", "cs_remark", "refund_tag", "order_num", "share_amount",
                            "spec_code", "goods_name", "goods_weight", "num"]
            order = BMSOrderInfo()
            for field in order_fields:
                setattr(order, field, row[field])
            if str(row["buyer_nick"]) in ["nan", "NaN"]:
                order.src_tids = row["dealer_order_id"]
                order.shop_name = row["dealer_name"]
                order.buyer_nick = row["receiver_name"]
            if str(row["trade_no"]) in ["nan", "NaN"]:
                order.trade_no = order.src_tids
            if len(str(order.src_tids)) > 100:
                order.src_tids = str(order.src_tids)[:100]
            try:
                order.price = Decimal(float(order.share_amount) / int(order.num)).quantize(Decimal("0.00"))
            except:
                order.price = order.share_amount
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["trade_no"])
                report_dic["false"] += 1
        return report_dic


class OrderManageViewset(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = OriOrderInfoSerializer
    filter_class = OriOrderInfoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriOrderInfo.objects.none()
        queryset = OriOrderInfo.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriOrderInfoFilter(params)
        serializer = OriOrderInfoSerializer(f.qs, many=True)
        return Response(serializer.data)




















