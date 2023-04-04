# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm
from itertools import chain
from functools import reduce
from django.db.models import F, Q
import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import LabelCategory, Label, LogLabelCategory, LogLabel, LabelCustomerOrder, LabelCustomerOrderDetails, \
    LogLabelCustomerOrder
from apps.utils.orm.queryfunc import andconmbine, orconmbine


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
    code = django_filters.CharFilter(field_name="code", lookup_expr='exact')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    label__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = LabelCustomerOrder
        fields = "__all__"


class LabelCustomerOrderDetailsFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(method='customer_filter')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    order__label__name = django_filters.CharFilter(lookup_expr='icontains')
    order__name = django_filters.CharFilter(lookup_expr='icontains')
    order__code = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = LabelCustomerOrderDetails
        fields = "__all__"

    def customer_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset


