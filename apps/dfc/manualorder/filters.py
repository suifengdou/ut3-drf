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
    created_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    province__name = django_filters.CharFilter(lookup_expr='exact')
    city__name = django_filters.CharFilter(lookup_expr='exact')
    district__name = django_filters.CharFilter(lookup_expr='exact')
    mobile = django_filters.CharFilter(lookup_expr='icontains')
    memo = django_filters.CharFilter(lookup_expr='icontains')
    order_category = django_filters.CharFilter(method='multiple_filter')

    class Meta:
        model = ManualOrder
        fields = "__all__"

    def multiple_filter(self, queryset, name, *value):
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


class MOGoodsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    goods_name__name = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__mobile = django_filters.CharFilter()
    manual_order__erp_order_id = django_filters.CharFilter()
    manual_order__shop__name = django_filters.CharFilter(lookup_expr='icontains')
    manual_order__nickname = django_filters.CharFilter()
    manual_order__m_sn = django_filters.CharFilter()
    manual_order__department__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = MOGoods
        fields = "__all__"


class ManualOrderExportFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    updated_time = django_filters.DateTimeFromToRangeFilter()
    erp_order_id = django_filters.CharFilter(field_name="erp_order_id", lookup_expr='icontains')
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    goods_name = django_filters.CharFilter(field_name="goods_name", lookup_expr='icontains')
    warehouse__name = django_filters.CharFilter(field_name="goods_name", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    sign_range = django_filters.CharFilter(method='multiple_tag_filter')

    class Meta:
        model = ManualOrderExport
        fields = "__all__"

    def multiple_tag_filter(self, queryset, name, *value):
        name = str(name).replace("_range", "")
        condition_list = str(value[0]).split(",")
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




