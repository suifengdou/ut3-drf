# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm
from django.db.models import F, Q

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import CSAddress
from apps.utils.orm.queryfunc import andconmbine


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class CSAddressFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter(method='customer_filter')
    city__name = django_filters.CharFilter()
    name = django_filters.CharFilter()
    mobile = django_filters.CharFilter()

    class Meta:
        model = CSAddress
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

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

