import datetime, math, re, inspect
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
from .models import CustomerLabelPerson, LogCustomerLabelPerson, CustomerLabelFamily, LogCustomerLabelFamily, \
    CustomerLabelProduct, LogCustomerLabelProduct, CustomerLabelOrder, LogCustomerLabelOrder, CustomerLabelService, \
    LogCustomerLabelService, CustomerLabelSatisfaction, LogCustomerLabelSatisfaction, CustomerLabelRefund, \
    LogCustomerLabelRefund, CustomerLabelOthers, LogCustomerLabelOthers
from .serializers import CustomerLabelPersonSerializer, CustomerLabelFamilySerializer, CustomerLabelProductSerializer,\
    CustomerLabelOrderSerializer, CustomerLabelServiceSerializer, CustomerLabelSatisfactionSerializer, \
    CustomerLabelRefundSerializer, CustomerLabelOthersSerializer
from .filters import CustomerLabelPersonFilter, CustomerLabelFamilyFilter, CustomerLabelProductFilter, \
    CustomerLabelOrderFilter, CustomerLabelServiceFilter, CustomerLabelSatisfactionFilter, \
    CustomerLabelRefundFilter, CustomerLabelOthersFilter
from apps.utils.logging.loggings import logging, getlogs
from apps.crm.labels.models import Label
from apps.crm.customers.models import Customer, LogCustomer


class CustomerLabelPersonViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelPersonSerializer
    filter_class = CustomerLabelPersonFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelPerson.objects.none()
        queryset = CustomerLabelPerson.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelPersonFilter(params)
        serializer = CustomerLabelPersonSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelPersonFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelPerson.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelPerson.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelPerson)
        return Response(ret)


class CustomerLabelFamilyViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelFamilySerializer
    filter_class = CustomerLabelFamilyFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelFamily.objects.none()
        queryset = CustomerLabelFamily.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelFamilyFilter(params)
        serializer = CustomerLabelFamilySerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelFamilyFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelFamily.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelFamily.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelFamily)
        return Response(ret)


class CustomerLabelProductViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelProductSerializer
    filter_class = CustomerLabelProductFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelProduct.objects.none()
        queryset = CustomerLabelProduct.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelProductFilter(params)
        serializer = CustomerLabelProductSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelProductFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelProduct.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelProduct.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelProduct)
        return Response(ret)


class CustomerLabelOrderViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelOrderSerializer
    filter_class = CustomerLabelOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelOrder.objects.none()
        queryset = CustomerLabelOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelOrderFilter(params)
        serializer = CustomerLabelOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelOrder.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelOrder)
        return Response(ret)


class CustomerLabelServiceViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelServiceSerializer
    filter_class = CustomerLabelServiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelService.objects.none()
        queryset = CustomerLabelService.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelServiceFilter(params)
        serializer = CustomerLabelServiceSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelServiceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelService.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelService.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelService)
        return Response(ret)


class CustomerLabelSatisfactionViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelSatisfactionSerializer
    filter_class = CustomerLabelSatisfactionFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelSatisfaction.objects.none()
        queryset = CustomerLabelSatisfaction.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelSatisfactionFilter(params)
        serializer = CustomerLabelSatisfactionSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelSatisfactionFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelSatisfaction.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelSatisfaction.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelSatisfaction)
        return Response(ret)


class CustomerLabelRefundViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelRefundSerializer
    filter_class = CustomerLabelRefundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelRefund.objects.none()
        queryset = CustomerLabelRefund.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelRefundFilter(params)
        serializer = CustomerLabelRefundSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelRefundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelRefund.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelRefund.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelRefund)
        return Response(ret)


class CustomerLabelOthersViewset(viewsets.ModelViewSet):
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
    serializer_class = CustomerLabelOthersSerializer
    filter_class = CustomerLabelOthersFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['customers.view_customer']
    }

    def get_queryset(self):
        if not self.request:
            return CustomerLabelOthers.objects.none()
        queryset = CustomerLabelOthers.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CustomerLabelOthersFilter(params)
        serializer = CustomerLabelOthersSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CustomerLabelOthersFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = CustomerLabelOthers.objects.filter(id__in=order_ids, order_status=1)
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
        instance = CustomerLabelOthers.objects.filter(id=id)[0]
        ret = getlogs(instance, LogCustomerLabelOthers)
        return Response(ret)


def get_serializer(label):
    customer_label_dict = {
        "PPL": CustomerLabelPersonSerializer,
        "FAM": CustomerLabelFamilySerializer,
        "PROD": CustomerLabelProductSerializer,
        "ORD": CustomerLabelOrderSerializer,
        "SVC": CustomerLabelServiceSerializer,
        "SAT": CustomerLabelSatisfactionSerializer,
        "REFD": CustomerLabelRefundSerializer,
        "OTHS": CustomerLabelOthersSerializer
    }
    serializers_class = customer_label_dict.get(label.group, None)
    return serializers_class


def get_model(label):
    customer_label_dict = {
        "PPL": CustomerLabelPerson,
        "FAM": CustomerLabelFamily,
        "PROD": CustomerLabelProduct,
        "ORD": CustomerLabelOrder,
        "SVC": CustomerLabelService,
        "SAT": CustomerLabelSatisfaction,
        "REFD": CustomerLabelRefund,
        "OTHS": CustomerLabelOthers
    }
    model_class = customer_label_dict.get(label.group, None)
    return model_class


def get_logmodel(label):
    customer_label_dict = {
        "PPL": LogCustomerLabelPerson,
        "FAM": LogCustomerLabelFamily,
        "PROD": LogCustomerLabelProduct,
        "ORD": LogCustomerLabelOrder,
        "SVC": LogCustomerLabelService,
        "SAT": LogCustomerLabelSatisfaction,
        "REFD": LogCustomerLabelRefund,
        "OTHS": LogCustomerLabelOthers
    }
    model_class = customer_label_dict.get(label.group, None)
    return model_class


def QueryLabel(label, customer):
    if isinstance(label, Label):
        label_obj = label
        model_class = get_model(label)

    else:
        return None
    if isinstance(customer, Customer):
        customer_obj = customer
    else:
        return None
    data_query = {
        "customer": customer_obj,
        "label": label_obj,
    }
    _q_customer_label_obj = model_class.objects.filter(**data_query)
    if _q_customer_label_obj.exists():
        customer_label_obj = _q_customer_label_obj[0]
        return customer_label_obj
    else:
        return None


def CreateLabel(label, customer, user):
    if isinstance(label, Label):
        label_obj = label
        model_class = get_model(label)
        logmodel_class = get_logmodel(label)
        if not model_class:
            return False
    else:
        return False
    if isinstance(customer, Customer):
        customer_obj = customer
    else:
        return False
    data = {
        "customer": customer_obj,
        "label": label_obj,
        "creator": user.username
    }
    try:
        customer_label_obj = model_class.objects.create(**data)
        logging(customer_label_obj, user, logmodel_class, "创建标签")
        logging(customer, user, LogCustomer, "创建标签：%s" % str(label_obj.name))
        return True
    except Exception as e:
        return False


def DeleteLabel(label, customer, user):
    if isinstance(label, Label):
        label_obj = label
        model_class = get_model(label)
        serializer_class = get_serializer(label)
        if not all((model_class, serializer_class)):
            return False
    else:
        return False
    if isinstance(customer, Customer):
        customer_obj = customer
    else:
        return False
    data_query = {
        "customer": customer_obj,
        "label": label_obj,
    }
    _q_customer_label_obj = model_class.objects.filter(**data_query)
    if _q_customer_label_obj.exists():
        customer_label_obj = _q_customer_label_obj[0]
    else:
        return False
    data_partial = {
        "is_delete": True,
    }
    serializer = serializer_class(customer_label_obj, data=data_partial, partial=True)
    try:
        serializer.is_valid()
        serializer.save()
        logging(customer_obj, user, LogCustomer, "删除标签：%s" % str(label_obj.name))
        return True
    except Exception as e:
        return False


def RecoverLabel(customer_label, label, user):
    if isinstance(label, Label):
        label_obj = label
        serializer_class = get_serializer(label)
        if not serializer_class:
            return False
    else:
        return False
    data_partial = {
        "is_delete": False,
    }
    serializer = serializer_class(customer_label, data=data_partial, partial=True)
    try:
        serializer.is_valid()
        serializer.save()
        logging(customer_label.customer, user, LogCustomer, "恢复标签：%s" % str(label_obj.name))
        return True
    except Exception as e:
        return False


