# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import ManualOrder, MOGoods, ManualOrderExport

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class ManualOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    province__name = django_filters.CharFilter(lookup_expr='exact')
    city__name = django_filters.CharFilter(lookup_expr='exact')
    district__name = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = ManualOrder
        fields = "__all__"


class MOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    manual_order__mobile = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__erp_order_id = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__shop__name = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__nickname = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__m_sn = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__department__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = MOGoods
        fields = "__all__"


class ManualOrderExportFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    erp_order_id = django_filters.CharFilter(field_name="erp_order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = ManualOrderExport
        fields = "__all__"






