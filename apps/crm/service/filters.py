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
    process_tag__in = NumberInFilter(field_name="process_tag", lookup_expr="in")
    sign__in = NumberInFilter(field_name="sign", lookup_expr="in")
    created_time = django_filters.DateTimeFromToRangeFilter()
    purchase_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    ori_create_time = django_filters.DateTimeFromToRangeFilter()
    finish_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(method='order_id_filter')

    class Meta:
        model = OriMaintenance
        fields = "__all__"

    def order_id_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset


class MaintenanceFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    ori_create_time = django_filters.DateTimeFromToRangeFilter()
    finish_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    repeat_tag__in = NumberInFilter(field_name="repeat_tag", lookup_expr="in")
    goods_name__in = NumberInFilter(field_name="goods_name", lookup_expr="in")

    class Meta:
        model = Maintenance
        fields = "__all__"


class MaintenanceSummaryFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = MaintenanceSummary
        fields = "__all__"






