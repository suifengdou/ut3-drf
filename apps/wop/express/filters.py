# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import ExpressWorkOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class ExpressWorkOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    mid_handler__in = NumberInFilter(field_name="mid_handler", lookup_expr="in")


    class Meta:
        model = ExpressWorkOrder
        fields = "__all__"

