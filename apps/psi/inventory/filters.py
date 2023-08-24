# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Inventory

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class InventoryFilter(django_filters.FilterSet):
    goods_name__name = django_filters.CharFilter(lookup_expr='icontains')
    warehouse__name =  django_filters.CharFilter(lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Inventory
        fields = "__all__"

