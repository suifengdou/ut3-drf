import datetime, math, re
import pandas as pd
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
from .models import Customer, LogCustomer
from .serializers import CustomerSerializer, CustomerLabelSerializer
from .filters import CustomerFilter
from apps.utils.logging.loggings import logging, getlogs, getfiles
from apps.wop.job.models import JobOrder, JobOrderDetails, LogJobOrder, LogJobOrderDetails
from ut3.settings import EXPORT_TOPLIMIT


class CustomerViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerSerializer
    filter_class = CustomerFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Customer.objects.none()
        queryset = Customer.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerFilter(params)
        serializer = CustomerSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Customer.objects.filter(id__in=order_ids, order_status=1)
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
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Customer.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomer)
        return Response(ret)


class CustomerLabelViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelSerializer
    filter_class = CustomerFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Customer.objects.none()
        queryset = Customer.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = CustomerFilter(params)
        serializer = CustomerLabelSerializer(f.qs[:200], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = CustomerFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Customer.objects.filter(id__in=order_ids)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def create_job(self, request, *args, **kwargs):
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
            _q_job_order = JobOrder.objects.filter(name__icontains="TEMP", order_status=1, department=user.department)
            if _q_job_order.exists():
                raise serializers.ValidationError({"创建错误": "已存在临时任务单，不可同时存在多个临时任务单 ！"})
            else:
                serial_number = re.sub("[- .:]", "", str(datetime.datetime.today().date()))
                job_dict = {
                    "name": "TEMP-%s-%s" % (user.department.name, user.username),
                    "code": "TEMP-%s" % serial_number,
                    "department": user.department,
                    "center": user.department.center,
                    "quantity": n,
                    "creator": user.username,
                }
                try:
                    job_order = JobOrder.objects.create(**job_dict)
                    logging(job_order, user, LogJobOrder, "创建")
                except Exception as e:
                    raise serializers.ValidationError({"创建错误": "错误原因为：%s" % e})
            for obj in check_list:
                job_details_dict = {
                    "order": job_order,
                    "customer": obj,
                    "creator": user.username,
                }
                try:
                    job_order_detail = JobOrderDetails.objects.create(**job_details_dict)
                    logging(job_order_detail, user, LogJobOrderDetails, "创建")
                except Exception as e:
                    data["error"].append(str(e))
                    n -= 1
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
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Customer.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomer)
        return Response(ret)






