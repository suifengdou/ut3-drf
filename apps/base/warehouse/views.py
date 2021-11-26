from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import WarehouseSerializer, WarehouseTypeSerializer
from .filters import WarehouseFilter, WarehouseTypeFilter
from .models import Warehouse, WarehouseType
from ut3.permissions import Permissions


class WarehouseViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定仓库
    list:
        返回仓库列表
    update:
        更新仓库信息
    destroy:
        删除仓库信息
    create:
        创建仓库信息
    partial_update:
        更新部分仓库字段
    """
    queryset = Warehouse.objects.all().order_by("id")
    serializer_class = WarehouseSerializer
    filter_class = WarehouseFilter
    filter_fields = ("name", "warehouse_id", "city", "receiver", "mobile",
                     "address", "category", "order_status", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['warehouse.view_warehouse']
    }


class WarehouseTypeViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定仓库类型
    list:
        返回仓库类型列表
    update:
        更新仓库类型信息
    destroy:
        删除仓库类型信息
    create:
        创建仓库类型信息
    partial_update:
        更新部分仓库类型字段
    """
    queryset = WarehouseType.objects.all().order_by("id")
    serializer_class = WarehouseTypeSerializer
    filter_class = WarehouseTypeFilter
    filter_fields = ("name", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['warehouse.view_warehouse']
    }