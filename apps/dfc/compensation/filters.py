# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Compensation, BatchCompensation, BCDetail

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class CompensationFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = Compensation
        fields = "__all__"


class BatchCompensationFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = BatchCompensation
        fields = "__all__"


class BCDetailFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    batch_order__order_id = django_filters.CharFilter(lookup_expr='iexact')
    batch_order__oa_order_id = django_filters.CharFilter(lookup_expr='iexact')
    batch_order__shop__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = BCDetail
        fields = "__all__"






