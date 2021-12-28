# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter
from .models import Specialist, VIPWechat

class NumberInFilter(BaseInFilter, NumberFilter):
    pass

class SpecialistFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Specialist
        fields = "__all__"


class VIPWechatFilter(django_filters.FilterSet):
    specialist__name = django_filters.CharFilter(lookup_expr='icontains')
    specialist__smartphone = django_filters.CharFilter(lookup_expr='icontains')
    customer__name = django_filters.CharFilter(lookup_expr='icontains')
    cs_wechat__in = NumberInFilter(field_name='name', lookup_expr='in')

    class Meta:
        model = VIPWechat
        fields = "__all__"


