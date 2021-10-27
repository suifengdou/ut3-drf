# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import DealerParts, DPGoods

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class DealerPartsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DealerParts
        fields = "__all__"


class DPGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    dealer_parts__mobile = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = DPGoods
        fields = "__all__"





