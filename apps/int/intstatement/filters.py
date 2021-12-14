# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import IntStatement


class IntStatementFilter(django_filters.FilterSet):
    ipo__order_id = django_filters.CharFilter(lookup_expr='icontains')
    ipo__distributor__name = django_filters.CharFilter(lookup_expr='icontains')
    receipt__order_id = django_filters.CharFilter(lookup_expr='icontains')
    receipt__bank_sn = django_filters.CharFilter(lookup_expr='icontains')
    receipt__payment_account = django_filters.CharFilter(lookup_expr='icontains')
    account__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = IntStatement
        fields = "__all__"






