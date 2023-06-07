# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import ExpressWorkOrder, EWOPhoto, LogExpressOrder


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class ExpressWorkOrderFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    submit_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    updated_time = django_filters.DateTimeFromToRangeFilter()
    information = django_filters.CharFilter(field_name="information", lookup_expr='icontains')
    suggestion = django_filters.CharFilter(field_name="suggestion", lookup_expr='icontains')
    feedback = django_filters.CharFilter(field_name="feedback", lookup_expr='icontains')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    track_id__in = CharInFilter(field_name="track_id", lookup_expr="in")

    class Meta:
        model = ExpressWorkOrder
        fields = "__all__"


class EWOPhotoFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = EWOPhoto
        fields = "__all__"


class LogExpressOrderFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = LogExpressOrder
        fields = "__all__"

