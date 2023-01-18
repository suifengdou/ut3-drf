import pandas as pd
import numpy as np
import datetime
import re
from functools import reduce
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ProductCatalogSerializer
from .models import ProductCatalog
from .filters import ProductCatalogFilter
from ut3.permissions import Permissions
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.decorators import action


class ProductCatalogMyselfViewset(viewsets.ModelViewSet):
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
    queryset = ProductCatalog.objects.all().order_by("id")
    serializer_class = ProductCatalogSerializer
    filter_class = ProductCatalogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['productcatalog.view_user_productcatalog',]
    }

    def get_queryset(self):
        if not self.request:
            return ProductCatalog.objects.none()
        user = self.request.user
        queryset = ProductCatalog.objects.filter(department=user.department).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ProductCatalogFilter(params)
        serializer = ProductCatalogSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = ProductCatalogFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ProductCatalog.objects.filter(id__in=order_ids)
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
            check_list.update(order_status=1)
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


class ProductCatalogManageViewset(viewsets.ModelViewSet):
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
    queryset = ProductCatalog.objects.all().order_by("id")
    serializer_class = ProductCatalogSerializer
    filter_class = ProductCatalogFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['productcatalog.view_productcatalog',]
    }

    def get_queryset(self):
        if not self.request:
            return ProductCatalog.objects.none()
        queryset = ProductCatalog.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ProductCatalogFilter(params)
        serializer = ProductCatalogSerializer(f.qs, many=True)
        return Response(serializer.data)


# class FreightViewset(viewsets.ModelViewSet):
#     """
#     retrieve:
#         返回指定货品明细
#     list:
#         返回货品明细
#     update:
#         更新货品明细
#     destroy:
#         删除货品明细
#     create:
#         创建货品明细
#     partial_update:
#         更新部分货品明细
#     """
#     queryset = Freight.objects.all().order_by("id")
#     serializer_class = FreightSerializer
#     filter_class = FreightFilter
#     filter_fields = "__all__"
#     permission_classes = (IsAuthenticated, Permissions)
#     extra_perm_map = {
#         "GET": ['productcatalog.view_productcatalog',]
#     }
#
#     def get_queryset(self):
#         if not self.request:
#             return Freight.objects.none()
#         queryset = Freight.objects.all().order_by("id")
#         return queryset
#
#     @action(methods=['patch'], detail=False)
#     def export(self, request, *args, **kwargs):
#         user = self.request.user
#         if not user.is_our:
#             request.data["creator"] = user.username
#         request.data.pop("page", None)
#         request.data.pop("allSelectTag", None)
#         params = request.data
#         f = FreightFilter(params)
#         serializer = FreightSerializer(f.qs, many=True)
#         return Response(serializer.data)


