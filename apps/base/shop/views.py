from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ShopSerializer, PlatformSerializer
from .filters import ShopFilter, PlatformFilter
from .models import Shop, Platform
from ut3.permissions import Permissions


class ShopViewset(viewsets.ModelViewSet):
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
    queryset = Shop.objects.all().order_by("id")
    serializer_class = ShopSerializer
    filter_class = ShopFilter
    filter_fields = ("name", "shop_id", "platform", "group_name", "company", "order_status", "create_time",
                     "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['shop.view_shop']
    }


class PlatformViewset(viewsets.ModelViewSet):
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
    queryset = Platform.objects.all().order_by("id")
    serializer_class = PlatformSerializer
    filter_class = PlatformFilter
    filter_fields = ("platform", "category", "order_status", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['shop.view_shop']
    }