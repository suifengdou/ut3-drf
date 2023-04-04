# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm


import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Servicer, DialogTB, DialogTBDetail, DialogTBWords, DialogJD, DialogJDDetail, DialogJDWords, \
    DialogOW, DialogOWDetail, DialogOWWords

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class ServicerFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Servicer
        fields = "__all__"


class DialogTBFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    customer = django_filters.CharFilter(field_name="customer", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DialogTB
        fields = "__all__"


class DialogTBDetailFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    sayer = django_filters.CharFilter(field_name="sayer", lookup_expr='icontains')
    content = django_filters.CharFilter(field_name="content", lookup_expr='icontains')
    dialog__customer =django_filters.CharFilter(lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DialogTBDetail
        fields = "__all__"


class DialogTBWordsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    words = django_filters.CharFilter(field_name="words", lookup_expr='icontains')

    class Meta:
        model = DialogTBWords
        fields = "__all__"


class DialogJDFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    customer = django_filters.CharFilter(field_name="customer", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DialogJD
        fields = "__all__"


class DialogJDDetailFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    sayer = django_filters.CharFilter(field_name="sayer", lookup_expr='icontains')
    content = django_filters.CharFilter(field_name="content", lookup_expr='icontains')
    dialog__customer = django_filters.CharFilter(lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    sayer__in = NumberInFilter(field_name="sayer", lookup_expr="in")

    class Meta:
        model = DialogJDDetail
        fields = "__all__"


class DialogJDWordsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    words = django_filters.CharFilter(field_name="words", lookup_expr='icontains')

    class Meta:
        model = DialogJDWords
        fields = "__all__"


class DialogOWFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    customer = django_filters.CharFilter(field_name="customer", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DialogOW
        fields = "__all__"


class DialogOWDetailFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    sayer = django_filters.CharFilter(field_name="sayer", lookup_expr='icontains')
    dialog__customer = django_filters.CharFilter(lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = DialogOWDetail
        fields = "__all__"


class DialogOWWordsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    words = django_filters.CharFilter(field_name="words", lookup_expr='icontains')

    class Meta:
        model = DialogOWWords
        fields = "__all__"



