# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm
from django.db.models import F, Q

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import CSGoods
from apps.utils.orm.queryfunc import andconmbine


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class CSGoodsFilter(django_filters.FilterSet):
    customer__name = django_filters.CharFilter()
    goods__name = django_filters.CharFilter()

    class Meta:
        model = CSGoods
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

