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

    class Meta:
        model = ManualOrder
        fields = "__all__"


class MOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    manual_order = django_filters.ModelChoiceFilter(to_field_name="erp_order_id", queryset=ManualOrder.objects.all())

    class Meta:
        model = MOGoods
        fields = "__all__"


class ManualOrderExportFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    erp_order_id = django_filters.CharFilter(field_name="erp_order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = ManualOrderExport
        fields = "__all__"






