# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Logistics, Deppon


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class LogisticsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = Logistics
        fields = "__all__"


class DepponFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')

    class Meta:
        model = Deppon
        fields = "__all__"

