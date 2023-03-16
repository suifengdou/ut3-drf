# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import JobCategory, JobOrder, JOFiles, JobOrderDetails, LogJobCategory, LogJobOrder, \
    LogJobOrderDetails, JODFiles
from apps.utils.orm.queryfunc import andconmbine, orconmbine


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
    order__code = django_filters.CharFilter(lookup_expr='icontains')
    customer__name = django_filters.CharFilter(lookup_expr='icontains')
    customer__name__in = django_filters.CharFilter(method='customer_filter')
    keywords = django_filters.CharFilter(method='keywords_filter')
    add_label = django_filters.CharFilter(method='keywords_filter')
    del_label = django_filters.CharFilter(method='keywords_filter')

    class Meta:
        model = JobOrderDetails
        fields = "__all__"

    def customer_filter(self, queryset, name, *value):
        name = name[:-4]
        condition_list = str(value[0]).split(",")
        condition = orconmbine(condition_list, name)
        if condition:
            queryset = queryset.filter(condition)
        else:
            queryset = queryset.none()
        return queryset

    def keywords_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class JOFilesFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = JOFiles
        fields = "__all__"


class JODFilesFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = JODFiles
        fields = "__all__"


