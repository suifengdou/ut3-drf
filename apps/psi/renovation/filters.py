# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Renovation, RenovationGoods, Renovationdetail, ROFiles


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class RenovationFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Renovation
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


class RenovationGoodsFilter(django_filters.FilterSet):
    order__code = django_filters.CharFilter()
    goods__name = django_filters.CharFilter(lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = RenovationGoods
        fields = "__all__"


class RenovationdetailFilter(django_filters.FilterSet):
    order__code = django_filters.CharFilter()
    goods__name = django_filters.CharFilter(lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Renovationdetail
        fields = "__all__"


class ROFilesFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ROFiles
        fields = "__all__"






