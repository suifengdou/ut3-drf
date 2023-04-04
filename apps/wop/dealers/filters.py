# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import DealerWorkOrder

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class DealerWorkOrderFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    submit_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    suggestion = django_filters.CharFilter(field_name="suggestion", lookup_expr='icontains')
    feedback = django_filters.CharFilter(field_name="feedback", lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DealerWorkOrder
        fields = "__all__"

