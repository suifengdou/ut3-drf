# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import WarehouseType, Warehouse

class WarehouseTypeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = WarehouseType
        fields = ["category", "create_time", "update_time", "is_delete", "creator"]


class WarehouseFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Warehouse
        fields = ["name", "warehouse_id", "city", "receiver", "mobile",
                  "address", "category", "order_status", "create_time", "update_time", "is_delete", "creator"]