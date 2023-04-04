# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriCallLog, CallLog


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class OriCallLogFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    call_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    answer_status = django_filters.CharFilter(field_name="answer_status", lookup_expr='icontains')
    satisfaction = django_filters.CharFilter(field_name="satisfaction", lookup_expr='icontains')
    remark = django_filters.CharFilter(field_name="remark", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OriCallLog
        fields = "__all__"


class CallLogFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    call_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = CallLog
        fields = "__all__"






