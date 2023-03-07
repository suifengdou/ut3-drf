# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import Goods, GoodsCategory


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class GoodsFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    goods_id = django_filters.CharFilter(field_name="goods_id", lookup_expr='icontains')
    goods_number = django_filters.CharFilter(field_name="goods_number", lookup_expr='icontains')
    goods_id__in = CharInFilter(lookup_expr='in')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Goods
        fields = "__all__"


class GoodsCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    code = django_filters.CharFilter(field_name="code", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = GoodsCategory
        fields = "__all__"

