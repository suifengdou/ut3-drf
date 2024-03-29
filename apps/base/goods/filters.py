# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import Goods, GoodsCategory, Bom


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class GoodsFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='keywords_filter')
    goods_number = django_filters.CharFilter(field_name="goods_number")
    goods_id_range = django_filters.CharFilter(method='multi_filter')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Goods
        fields = "__all__"

    def keywords_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            if "^" in condition_list[0]:
                name = name.replace("icontains", "iexact")
                value = str(condition_list[0]).replace("^", "")
                queryset = queryset.filter(**{name: value})
            else:
                queryset = queryset.filter(**{name: condition_list[0]})
        else:
            for value in condition_list:
                queryset = queryset.filter(**{name: value})
        return queryset

    def multi_filter(self, queryset, name, *value):
        name = str(name).replace("_range", "")
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


class GoodsCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    code = django_filters.CharFilter(field_name="code", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = GoodsCategory
        fields = "__all__"


class BomFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Bom
        fields = "__all__"



