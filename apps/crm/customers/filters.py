# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm
from django.db.models import F, Q

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import Customer
from apps.utils.orm.queryfunc import andconmbine


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    customerlabelperson__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelfamilay__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelproduct__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelorder__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelservice__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelsatisfacition__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelrefund__label__name = django_filters.CharFilter(method='clabel_filter')
    customerlabelothers__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = Customer
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            for value in condition_list:
                queryset = queryset.filter(**{name: value})
        return queryset

