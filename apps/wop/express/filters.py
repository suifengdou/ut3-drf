# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import ExpressWorkOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class ExpressWorkOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    submit_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    suggestion = django_filters.CharFilter(field_name="suggestion", lookup_expr='icontains')
    feedback = django_filters.CharFilter(field_name="feedback", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = ExpressWorkOrder
        fields = "__all__"

