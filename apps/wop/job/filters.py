# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import JobCategory, JobOrder, JOFiles, JobOrderDetails, LogJobCategory, LogJobOrder, \
    LogJobOrderDetails, InvoiceJobOrder, IJOGoods, LogInvoiceJobOrder, LogIJOGoods, JODFiles


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class JobCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(lookup_expr='in')

    class Meta:
        model = JobCategory
        fields = "__all__"


class JobOrderFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(lookup_expr='in')

    class Meta:
        model = JobOrder
        fields = "__all__"


class JobOrderDetailsFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = JobOrderDetails
        fields = "__all__"


class InvoiceJobOrderFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = InvoiceJobOrder
        fields = "__all__"


class IJOGoodsFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(lookup_expr='exact')
    label__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = IJOGoods
        fields = "__all__"


