# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriOrderInfo, OrderInfo, BMSOrderInfo

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class OriOrderInfoFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    trade_no = django_filters.CharFilter(field_name="trade_no", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OriOrderInfo
        fields = "__all__"

class BMSOrderInfoFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    trade_no = django_filters.CharFilter(field_name="trade_no", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = BMSOrderInfo
        fields = "__all__"


class OrderInfoFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    trade_no = django_filters.CharFilter(field_name="trade_no", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OrderInfo
        fields = "__all__"