# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import OriSatisfactionWorkOrder, OSWOFiles, SatisfactionWorkOrder, SWOProgress, SWOPFiles, ServiceWorkOrder, InvoiceWorkOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class OriSatisfactionWorkOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = OriSatisfactionWorkOrder
        fields = "__all__"


class OSWOFilesFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OSWOFiles
        fields = "__all__"


class SWOFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(lookup_expr='icontains')
    goods_name__name = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    completed_time = django_filters.DateTimeFromToRangeFilter()
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    stage__in = NumberInFilter(field_name="stage", lookup_expr="in")
    cs_level__in = NumberInFilter(field_name="cs_level", lookup_expr="in")


    class Meta:
        model = SatisfactionWorkOrder
        fields = "__all__"


class SWOProgressFilter(django_filters.FilterSet):
    order__order_id = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    content = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = SWOProgress
        fields = "__all__"


class SWOPFilesFilter(django_filters.FilterSet):
    workorder__order_id = django_filters.CharFilter(lookup_expr='icontains')
    workorder__title = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = SWOPFiles
        fields = "__all__"


class ServiceWorkOrderFilter(django_filters.FilterSet):
    swo_order__order_id = django_filters.CharFilter(lookup_expr='icontains')
    swo_order__title = django_filters.CharFilter(lookup_expr='icontains')
    customer__name = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = ServiceWorkOrder
        fields = "__all__"


class InvoiceWorkOrderFilter(django_filters.FilterSet):
    swo_order__order_id = django_filters.CharFilter(lookup_expr='icontains')
    swo_order__title = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")


    class Meta:
        model = InvoiceWorkOrder
        fields = "__all__"





