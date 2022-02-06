import pandas as pd
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import CurrencySerializer, IntAccountSerializer
from .filters import CurrencyFilter, IntAccountFilter
from .models import Currency, IntAccount
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from ut3.settings import EXPORT_TOPLIMIT


class CurrencyViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定币种
    list:
        返回币种列表
    update:
        更新币种信息
    destroy:
        删除币种信息
    create:
        创建币种信息
    partial_update:
        更新部分币种字段
    """
    serializer_class = CurrencySerializer
    filter_class = CurrencyFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['intpurchase.view_user_intpurchaseorder', 'intpurchase.view_handler_intpurchaseorder']
    }

    def get_queryset(self):
        if not self.request:
            return Currency.objects.none()
        queryset = Currency.objects.all().order_by("id")
        return queryset


    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f =CurrencyFilter(params)
        serializer = CurrencySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


class IntAccountViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定国际账户
    list:
        返回国际账户列表
    update:
        更新国际账户信息
    destroy:
        删除国际账户信息
    create:
        创建国际账户信息
    partial_update:
        更新部分国际账户字段
    """
    serializer_class = IntAccountSerializer
    filter_class = IntAccountFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['intpurchase.view_user_intpurchaseorder', 'intpurchase.view_handler_intpurchaseorder']
    }

    def get_queryset(self):
        if not self.request:
            return IntAccount.objects.none()
        queryset = IntAccount.objects.all().order_by("id")
        return queryset


    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = IntAccountFilter(params)
        serializer = IntAccountSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)



