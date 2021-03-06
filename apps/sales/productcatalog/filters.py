# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import ProductCatalog


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class ProductCatalogFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    goods__name = django_filters.CharFilter(lookup_expr='icontains')
    company__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ProductCatalog
        fields = "__all__"
