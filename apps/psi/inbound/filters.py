# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriInbound, Inbound, InboundDetail


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class OriInboundFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OriInbound
        fields = "__all__"

class InboundFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = Inbound
        fields = "__all__"



class InboundDetailFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = InboundDetail
        fields = "__all__"









