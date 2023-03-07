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
from .models import LabelCategory, Label, LogLabelCategory, LogLabel, LabelCustomerOrder, LabelCustomerOrderDetails, \
    LabelCustomer, LogLabelCustomerOrder, LogLabelCustomer, LogLabelCustomerOrderDetails
from apps.utils.logging.loggings import logging
from .serializers import LabelCategorySerializer, LabelSerializer, LabelCustomerOrderSerializer, LabelCustomerSerializer, LabelCustomerOrderDetailsSerializer
from .filters import LabelCategoryFilter, LabelFilter, LabelCustomerOrderFilter, LabelCustomerFilter, LabelCustomerOrderDetailsFilter
from apps.utils.logging.loggings import logging, getlogs
from apps.crm.customers.models import Customer, LogCustomer
from ut3.settings import EXPORT_TOPLIMIT
from apps.wop.job.models import JobOrder, JobOrderDetails, LogJobOrder, LogJobOrderDetails


class LabelCategoryViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCategorySerializer
    filter_class = LabelCategoryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCategory.objects.none()
        queryset = LabelCategory.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCategoryFilter(params)
        serializer = LabelCategorySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = LabelCategory.objects.filter(id=id)[0]
        ret = getlogs(instance, LogLabelCategory)
        return Response(ret)


class LabelCenterViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelSerializer
    filter_class = LabelFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return Label.objects.none()
        queryset = Label.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelFilter(params)
        serializer = LabelSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


class LabelViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelSerializer
    filter_class = LabelFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return Label.objects.none()
        queryset = Label.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelFilter(params)
        serializer = LabelSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Label.objects.filter(id=id)[0]
        ret = getlogs(instance, LogLabel)
        return Response(ret)


class LabelCustomerOrderSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderSerializer
    filter_class = LabelCustomerOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrder.objects.none()
        queryset = LabelCustomerOrder.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderFilter(params)
        serializer = LabelCustomerOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = LabelCustomerOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = LabelCustomerOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        user = request.user
        if not user.department.center:
            raise serializers.ValidationError({"error": "当前账号无中心！"})
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
                all_details = obj.labelcustomerorderdetails_set.all()
                check_all_details = all_details.filter(order_status=1)
                if check_all_details.exists():
                    obj.mistake_tag = 1
                    data["error"].append("存在未递交的明细")
                    obj.save()
                    n -= 1
                    continue
                details_error = 0
                for details in all_details:
                    _q_customer_label = LabelCustomer.objects.filter(customer=details.customer, label=obj.label)
                    if _q_customer_label.exists():
                        details.mistake_tag = 2
                        data["error"].append("%s 明细对应客户已存在标签" % details.customer.name)
                        obj.save()
                        n -= 1
                        details_error = 1
                        continue
                    else:
                        labelcustomer = LabelCustomer()
                        labelcustomer.label = obj.label
                        labelcustomer.customer = details.customer
                        labelcustomer.creator = user.username
                        labelcustomer.center = user.department.center
                        labelcustomer.memo = "来源：%s" % (obj.code)
                        try:
                            labelcustomer.save()
                            logging(labelcustomer, user, LogLabelCustomer, "创建")
                            details.order_status = 3
                            details.save()
                            logging(details, user, LogLabelCustomerOrderDetails, "审核")
                        except Exception as e:
                            details.mistake_tag = 3
                            data["error"].append("%s 创建标签出错" % details.customer.name)
                            obj.save()
                            n -= 1
                            details_error = 1
                            continue
                if details_error:
                    obj.mistake_tag = 2
                    data["error"].append("存在明细错误")
                    obj.save()
                    n -= 1
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogLabelCustomerOrder, "审核")
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


class LabelCustomerOrdercheckViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderSerializer
    filter_class = LabelCustomerOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrder.objects.none()
        queryset = LabelCustomerOrder.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderFilter(params)
        serializer = LabelCustomerOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = LabelCustomerOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = LabelCustomerOrder.objects.filter(id__in=order_ids, order_status=2)
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


class LabelCustomerOrderViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderSerializer
    filter_class = LabelCustomerOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrder.objects.none()
        queryset = LabelCustomerOrder.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderFilter(params)
        serializer = LabelCustomerOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = LabelCustomerOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogLabelCustomerOrder)
        return Response(ret)


class LabelCustomerOrderDetailsSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderDetailsSerializer
    filter_class = LabelCustomerOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrderDetails.objects.none()
        queryset = LabelCustomerOrderDetails.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderDetailsFilter(params)
        serializer = LabelCustomerOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = LabelCustomerOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = LabelCustomerOrderDetails.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        user = request.user
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.order.order_status != 1:
                    obj.mistake_tag = 1
                    data["error"].append("%s 明细对应标签单状态错误" % obj.order.name)
                    obj.save()
                    n -= 1
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogLabelCustomerOrderDetails, "提交")
                obj.order.quantity += 1
                obj.order.save()
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
            '手机': 'customer',
            '标签关联单编码': 'code',
            '备注': 'memo',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["手机", "标签关联单编码", '备注']

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
            _ret_verify_field = LabelCustomerOrderDetails.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)
            code_dict = {}
            codes = list(set(df.code))
            for code in codes:
                _q_order = LabelCustomerOrder.objects.filter(code=code, order_status=1)
                if _q_order.exists():
                    code_dict[code] = _q_order[0]

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
                intermediate_report_dic = self.save_resources(request, _ret_list, code_dict)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            for code in codes:
                code_dict[code].quantity = code_dict[code].labelcustomerorderdetails_set.filter(order_status=1).count()
                code_dict[code].save()
                logging(code_dict[code], user, LogLabelCustomerOrder, "更新数量：%s" % code_dict[code].quantity)
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource, code_dict):
        # 设置初始报告

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:
            user = request.user
            order_details = LabelCustomerOrderDetails()
            order = code_dict.get(row["code"], None)
            if not order:
                report_dic["error"].append("%s 不存在待处理关联单" % row["code"])
                report_dic["false"] += 1
                continue
            order_details.order = order
            row["customer"] = re.sub("[!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(row["customer"]))
            if not re.match(r"^1[23456789]\d{9}$", row["customer"]):
                report_dic["error"].append("%s 电话不符合规则" % row["customer"])
                report_dic["false"] += 1
                continue
            _q_customer = Customer.objects.filter(name=row["customer"])
            if _q_customer.exists():
                customer = _q_customer[0]
                _q_repeated_details = LabelCustomerOrderDetails.objects.filter(order=order, customer=customer)
                if _q_repeated_details.exists():
                    report_dic["error"].append("%s 同一关联单电话重复" % row["customer"])
                    report_dic["false"] += 1
                    continue
                order_details.customer = customer
            else:
                customer = Customer.objects.create(**{"name": row["customer"]})
                logging(customer, user, LogCustomer, "由标签创建")
                order_details.customer = customer
            order_details.memo = row['memo']
            try:
                order_details.creator = user.username
                order_details.save()
                logging(order_details, user, LogLabelCustomerOrderDetails, "创建")
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
        return report_dic


class LabelCustomerOrderDetailsCheckViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderDetailsSerializer
    filter_class = LabelCustomerOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrderDetails.objects.none()
        queryset = LabelCustomerOrderDetails.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderDetailsFilter(params)
        serializer = LabelCustomerOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = LabelCustomerOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = LabelCustomerOrderDetails.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        user = request.user
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.order.order_status != 1:
                    obj.mistake_tag = 1
                    data["error"].append("%s 明细对应标签单状态错误" % obj.order.name)
                    obj.save()
                    n -= 1
                    continue
                _q_customer_label = LabelCustomer.objects.filter(customer=obj.customer, label=obj.order.label)
                if _q_customer_label.exists():
                    obj.mistake_tag = 2
                    data["error"].append("%s 明细对应客户已存在标签" % obj.customer.name)
                    obj.save()
                    n -= 1
                    continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogLabelCustomerOrderDetails, "审核")
                obj.order.quantity += 1
                obj.order.save()
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
            '手机': 'customer',
            '标签关联单编码': 'code',
            '备注': 'memo',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["手机", "标签关联单编码", '备注']

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                raise serializers.ValidationError("必要字段不全或者错误: %s" % e)

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = LabelCustomerOrderDetails.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)
            code_dict = {}
            codes = list(set(df.code))
            for code in codes:
                _q_order = LabelCustomerOrder.objects.filter(code=code, order_status=1)
                if _q_order.exists():
                    code_dict[code] = _q_order[0]

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
                intermediate_report_dic = self.save_resources(request, _ret_list, code_dict)
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
    def save_resources(request, resource, code_dict):
        # 设置初始报告

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:
            user = request.user
            order_details = LabelCustomerOrderDetails()
            order = code_dict.get(row["code"], None)
            if not order:
                report_dic["error"].append("%s 不存在待处理关联单" % row["code"])
                report_dic["false"] += 1
                continue
            order_details.order = order
            row["customer"] = re.sub("[!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(row["customer"]))
            if not re.match(r"^1[3456789]\d{9}$", row["customer"]):
                report_dic["error"].append("%s 电话不符合规则" % row["customer"])
                report_dic["false"] += 1
                continue
            _q_customer = Customer.objects.filter(name=row["customer"])
            if _q_customer.exists():
                customer = _q_customer[0]
                _q_repeated_details = LabelCustomerOrderDetails.objects.filter(order=order, customer=customer)
                if _q_repeated_details.exists():
                    report_dic["error"].append("%s 同一关联单电话重复" % row["customer"])
                    report_dic["false"] += 1
                    continue
                order_details.customer = customer
            else:
                customer = Customer()
                customer.name = row["customer"]
                customer.save()
                order_details.customer = customer
            order_details.memo = row['memo']
            try:
                order_details.creator = user.username
                order_details.save()
                logging(order_details, user, LogLabelCustomerOrderDetails, "创建")
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
        return report_dic


class LabelCustomerOrderDetailsViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerOrderDetailsSerializer
    filter_class = LabelCustomerOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomerOrderDetails.objects.none()
        queryset = LabelCustomerOrderDetails.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerOrderDetailsFilter(params)
        serializer = LabelCustomerOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = LabelCustomerOrderDetails.objects.filter(id=id)[0]
        ret = getlogs(instance, LogLabelCustomerOrderDetails)
        return Response(ret)


class LabelCustomerCenterViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerSerializer
    filter_class = LabelCustomerFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        user = self.request.user
        if not user.department.center:
            return LabelCustomer.objects.none()
        if not self.request:
            return LabelCustomer.objects.none()
        queryset = LabelCustomer.objects.filter(center=user.department.center).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerFilter(params)
        serializer = LabelCustomerSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["center"] = user.department.center
        if all_select_tag:
            handle_list = LabelCustomerFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = LabelCustomer.objects.filter(id__in=order_ids)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def create_order(self, request, *args, **kwargs):
        params = request.data
        user = request.user
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            order = JobOrder()
            serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
            for obj in check_list:
                if obj.order.order_status != 1:
                    obj.mistake_tag = 1
                    data["error"].append("%s 明细对应标签单状态错误" % obj.order.name)
                    obj.save()
                    n -= 1
                    continue
                _q_customer_label = LabelCustomer.objects.filter(customer=obj.customer, label=obj.order.label)
                if _q_customer_label.exists():
                    obj.mistake_tag = 2
                    data["error"].append("%s 明细对应客户已存在标签" % obj.customer.name)
                    obj.save()
                    n -= 1
                    continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogLabelCustomerOrderDetails, "审核")
                obj.order.quantity += 1
                obj.order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        user = request.user
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.order.order_status != 1:
                    obj.mistake_tag = 1
                    data["error"].append("%s 明细对应标签单状态错误" % obj.order.name)
                    obj.save()
                    n -= 1
                    continue
                _q_customer_label = LabelCustomer.objects.filter(customer=obj.customer, label=obj.order.label)
                if _q_customer_label.exists():
                    obj.mistake_tag = 2
                    data["error"].append("%s 明细对应客户已存在标签" % obj.customer.name)
                    obj.save()
                    n -= 1
                    continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogLabelCustomerOrderDetails, "审核")
                obj.order.quantity += 1
                obj.order.save()
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


class LabelCustomerViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定订单
    list:
        返回订单列表
    """
    serializer_class = LabelCustomerSerializer
    filter_class = LabelCustomerFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return LabelCustomer.objects.none()
        queryset = LabelCustomer.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = LabelCustomerFilter(params)
        serializer = LabelCustomerSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = LabelCustomer.objects.filter(id=id)[0]
        ret = getlogs(instance, LogLabelCustomer)
        return Response(ret)
















