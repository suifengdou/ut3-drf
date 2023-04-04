# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Currency, IntAccount

class CurrencyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Currency
        fields = "__all__"


class IntAccountFilter(django_filters.FilterSet):
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    coompany__name = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = IntAccount
        fields = "__all__"






