# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriMaintenance, Maintenance, MaintenanceSummary


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class OriMaintenanceFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = OriMaintenance
        fields = "__all__"


class MaintenanceFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    repeat_tag__in = NumberInFilter(field_name="repeat_tag", lookup_expr="in")
    goods_name__in = NumberInFilter(field_name="goods_name", lookup_expr="in")

    class Meta:
        model = Maintenance
        fields = "__all__"


class MaintenanceSummaryFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = MaintenanceSummary
        fields = "__all__"






