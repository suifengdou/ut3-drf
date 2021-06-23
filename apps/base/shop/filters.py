# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Shop, Platform

class ShopFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Shop
        fields = ["name", "shop_id", "platform", "group_name", "company", "order_status", "create_time",
                  "update_time", "is_delete", "creator"]


class PlatformFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Platform
        fields = ["name", "category", "order_status", "create_time", "update_time", "is_delete", "creator"]

