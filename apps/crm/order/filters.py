# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriOrder, DecryptOrder, LogOriOrder, LogDecryptOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class OriOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    trade_no = django_filters.CharFilter(field_name="trade_no", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OriOrder
        fields = "__all__"


class DecryptOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    trade_no = django_filters.CharFilter(field_name="trade_no", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    goods = django_filters.CharFilter(method='goods_filter')

    class Meta:
        model = DecryptOrder
        fields = "__all__"

    def goods_filter(self, queryset, name, *value):
        condition_list = value
        for condition in condition_list:
            queryset = queryset.filter(**{name: condition})
        return queryset


