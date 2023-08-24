import datetime, math
import pandas as pd
import re
from decimal import Decimal
import numpy as np
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import CNOrder, HistoryCNOrder, LogHistoryCNOrder, LogCNOrder
from .serializers import CNOrderSerializer, HistoryCNOrderSerializer
from .filters import CNOrderFilter, HistoryCNOrderFilter
from ut3.settings import EXPORT_TOPLIMIT
from apps.utils.logging.loggings import logging, getlogs
from apps.base.warehouse.models import Warehouse
from apps.base.shop.models import Shop
from apps.crm.customers.models import Customer


class CNOrderSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定专属客服
    list:
        返回专属客服
    update:
        更新专属客服
    destroy:
        删除专属客服
    create:
        创建专属客服
    partial_update:
        更新部分专属客服
    """
    serializer_class = CNOrderSerializer
    filter_class = CNOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['cnorder.view_cnorder']
    }

    def get_queryset(self):
        if not self.request:
            return CNOrder.objects.none()
        queryset = CNOrder.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = CNOrderFilter(params)
        serializer = CNOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CNOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CNOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):

        params = request.data
        relate_list = self.get_handle_list(params)
        n = len(relate_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in relate_list:
                if not all((obj.shop_name, obj.warehouse_name)):

                    obj.mistake_tag = 1
                    data["error"].append(f"{obj.scp_order_id}缺失店铺名称或仓库名称")
                    obj.save()
                    n -= 1
                    continue
                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse_name)
                if _q_warehouse.exists():
                    obj.warehouse = _q_warehouse[0]
                else:
                    obj.mistake_tag = 2
                    data["error"].append(f"{obj.scp_order_id}UT未创建此仓库{obj.warehouse_name}")
                    obj.save()
                    n -= 1
                    continue
                if obj.distributor_name:
                    _q_shop = Shop.objects.filter(name=obj.distributor_name)
                    if _q_shop.exists():
                        obj.shop = _q_shop[0]
                    else:
                        obj.mistake_tag = 3
                        data["error"].append(f"{obj.scp_order_id}UT未创建此店铺{obj.distributor_nanme}")
                        obj.save()
                        n -= 1
                        continue
                else:
                    _q_shop = Shop.objects.filter(name=obj.shop_name)
                    if _q_shop.exists():
                        obj.shop = _q_shop[0]
                    else:

                        obj.mistake_tag = 3
                        data["error"].append(f"{obj.scp_order_id}UT未创建此店铺{obj.shop_name}")
                        obj.save()
                        n -= 1
                        continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(relate_list) - n
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
        user = request.user
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            "店铺名称": "shop_name",
            "仓库名称": "warehouse_name",
            "货到付款": "is_cod",
            "下单时间": "order_time",
            "支付时间": "pay_time",
            "发货时间": "deliver_time",
            "签收时间": "sign_time",
            "订单类型": "order_category",
            "配送方式": "deliver_type",
            "状态": "ori_order_status",
            "系统单号": "scp_order_id",
            "交易订单号": "order_id",
            "外部订单号": "outside_order_id",
            "物流订单号": "odo_order_id",
            "仓库订单号": "warehouse_order_id",
            "快递公司": "logistics",
            "运单号": "track_no",
            "买家昵称": "nickname",
            "收货人姓名": "receiver",
            "省": "province",
            "市": "city",
            "区": "district",
            "街道": "town",
            "收货人地址": "address",
            "手机": "mobile",
            "电话": "telephone",
            "订单金额": "order_amount",
            "商品总售价": "order_total_amount",
            "快递费用": "express_fee",
            "COD服务费": "cod_fee",
            "实收金额": "paid_amount",
            "卖家备注": "remark",
            "退款": "is_refund",
            "赠品标识": "is_gift",
            "订货数量": "order_quantity",
            "商品售价": "price",
            "商品小计": "amount",
            "商品优惠": "discount",
            "货品编码": "goods_code",
            "商品名称": "goods_name",
            "商品重量(克)": "goods_weight",
            "分销商店铺名称": "distributor_name",
            "分销订单号": "distributor_order_id",
            "实发数量": "quantity",
            "货品唯一码": "sn"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["店铺名称", "仓库名称", "货到付款", "下单时间", "支付时间", "发货时间", "签收时间",
                             "订单类型", "配送方式", "状态", "系统单号", "交易订单号", "外部订单号", "物流订单号",
                             "仓库订单号", "快递公司", "运单号", "买家昵称", "收货人姓名", "省", "市", "区", "街道",
                             "收货人地址", "手机", "电话", "订单金额", "商品总售价", "快递费用", "COD服务费", "实收金额",
                             "卖家备注", "退款", "赠品标识", "订货数量", "商品售价", "商品小计", "商品优惠", "货品编码",
                             "商品名称", "商品重量(克)", "分销商店铺名称", "分销订单号", "实发数量", "货品唯一码"]

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
            _ret_verify_field = CNOrder.verify_mandatory(columns_key)
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
    def save_resources(request, resource, *args):
        # 设置初始报告
        user = request.user
        order_fields = ["shop_name", "warehouse_name", "is_cod", "order_time", "pay_time", "deliver_time", "sign_time",
                        "order_category", "deliver_type", "ori_order_status", "scp_order_id", "order_id",
                        "outside_order_id", "odo_order_id", "warehouse_order_id", "logistics", "track_no",
                        "nickname", "receiver", "province", "city", "district", "town", "address", "mobile",
                        "telephone", "order_amount", "order_total_amount", "express_fee", "cod_fee", "paid_amount",
                        "remark", "is_refund", "is_gift", "order_quantity", "price", "amount", "discount",
                        "goods_code", "goods_name", "goods_weight", "distributor_name", "distributor_order_id",
                        "quantity", "sn"]
        overflow_fields = ["track_no", "remark"]
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        for row in resource:
            _q_order = CNOrder.objects.filter(scp_order_id=row["scp_order_id"], goods_code=row["goods_code"])
            if _q_order.exists():
                report_dic["error"].append(f"{row['scp_order_id']}的{row['goods_code']}重复导入")
                report_dic["false"] += 1
                continue
            else:
                order = CNOrder()

            row["mobile"] = re.sub("[!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(row["mobile"]))
            if re.match(r"^1[23456789]\d{9}$", row["mobile"]):
                order.is_decrypt = True

            for keyword in overflow_fields:
                if len(str(row[keyword])) > 100:
                    row[keyword] = str(row[keyword])[:100]

            for keyword in order_fields:
                value = str(row[keyword])
                if value not in ["NaN", "nan"]:
                    setattr(order, keyword, row[keyword])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
                logging(order, user, LogCNOrder, "导入菜鸟发货明细")
            except Exception as e:
                report_dic['error'].append(f"{row['scp_order_id']} 保存出错: {e}")
                report_dic["false"] += 1
        return report_dic


class CNOrderManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定专属客服
    list:
        返回专属客服
    update:
        更新专属客服
    destroy:
        删除专属客服
    create:
        创建专属客服
    partial_update:
        更新部分专属客服
    """
    serializer_class = CNOrderSerializer
    filter_class = CNOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['cnorder.view_cnorder']
    }

    def get_queryset(self):
        if not self.request:
            return CNOrder.objects.none()
        queryset = CNOrder.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = CNOrderFilter(params)
        serializer = CNOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CNOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CNOrder.objects.filter(id__in=order_ids, order_status=1)
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
            for order in check_list:
                pass
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = CNOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCNOrder)
        return Response(ret)
