import pandas as pd
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ExpressCategorySerializer, ExpressSerializer
from .filters import ExpressCategoryFilter, ExpressFilter
from .models import ExpressCategory, Express, LogExpress
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from apps.utils.logging.loggings import getlogs, logging


class ExpressCategoryViewset(viewsets.ModelViewSet):
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
    queryset = ExpressCategory.objects.all().order_by("id")
    serializer_class = ExpressCategorySerializer
    filter_class = ExpressCategoryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressCategoryFilter(params)
        serializer = ExpressCategorySerializer(f.qs[:2000], many=True)
        return Response(serializer.data)


class ExpressViewset(viewsets.ModelViewSet):
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
    queryset = Express.objects.all().order_by("id")
    serializer_class = ExpressSerializer
    filter_class = ExpressFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressFilter(params)
        serializer = ExpressSerializer(f.qs[:2000], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Express.objects.filter(id=id)[0]
        ret = getlogs(instance, LogExpress)
        return Response(ret)
