# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import CNOrder, HistoryCNOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CNOrderFilter(django_filters.FilterSet):
    shop__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = CNOrder
        fields = "__all__"


class HistoryCNOrderFilter(django_filters.FilterSet):
    shop__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = HistoryCNOrder
        fields = "__all__"


