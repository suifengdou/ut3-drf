# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import IntReceipt


class IntReceiptFilter(django_filters.FilterSet):
    account__name = django_filters.CharFilter(lookup_expr='icontains')
    currency__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = IntReceipt
        fields = "__all__"






