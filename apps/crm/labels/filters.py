# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import LabelCategory, Label, LogLabelCategory, LogLabel, LabelCustomerOrder, LabelCustomerOrderDetails, \
    LabelCustomer, LogLabelCustomerOrder, LogLabelCustomer


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class LabelCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(lookup_expr='in')

    class Meta:
        model = LabelCategory
        fields = "__all__"


class LabelFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(lookup_expr='in')

    class Meta:
        model = Label
        fields = "__all__"


class LabelCustomerOrderFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = LabelCustomerOrder
        fields = "__all__"


class LabelCustomerOrderDetailsFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = LabelCustomerOrderDetails
        fields = "__all__"


class LabelCustomerFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(lookup_expr='exact')
    label__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = LabelCustomer
        fields = "__all__"


