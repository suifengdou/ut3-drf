# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Customer

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = NumberInFilter(field_name='name', lookup_expr='in')

    class Meta:
        model = Customer
        fields = "__all__"
