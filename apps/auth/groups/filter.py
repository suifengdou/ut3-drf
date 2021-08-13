# -*- coding: utf-8 -*-
# @Time    : 2021/2/2 15:05
# @Author  : Hann
# @Site    : 
# @File    : filter.py
# @Software: PyCharm

import django_filters

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission


class GroupFilter(django_filters.FilterSet):
    """
    Group 搜索类
    """
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Group
        fields = "__all__"


class PermissionFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Permission
        fields = "__all__"