# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import IntPurchaseOrder, IPOGoods, ExceptionIPO, EIPOGoods


class IntPurchaseOrderFilter(django_filters.FilterSet):
    distributor__name = django_filters.CharFilter(lookup_expr='icontains')
    account__name = django_filters.CharFilter(lookup_expr='icontains')
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    department__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = IntPurchaseOrder
        fields = "__all__"


class IPOGoodsFilter(django_filters.FilterSet):
    ipo__order_id = django_filters.CharFilter(lookup_expr='icontains')
    ipo__distributor__name = django_filters.CharFilter(lookup_expr='icontains')
    ipo__account__name = django_filters.CharFilter(lookup_expr='icontains')
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    goods_name__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = IPOGoods
        fields = "__all__"


class ExceptionIPOFilter(django_filters.FilterSet):
    distributor__name = django_filters.CharFilter(lookup_expr='icontains')
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    department__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ExceptionIPO
        fields = "__all__"


class EIPOGoodsFilter(django_filters.FilterSet):
    eipo__order_id = django_filters.CharFilter(lookup_expr='icontains')
    eipo__distributor__name = django_filters.CharFilter(lookup_expr='icontains')
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    goods_name__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = EIPOGoods
        fields = "__all__"





