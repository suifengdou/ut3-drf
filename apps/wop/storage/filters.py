# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import StorageWorkOrder

class StorageWorkOrderFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(field_name="keyword", lookup_expr='icontains')

    class Meta:
        model = StorageWorkOrder
        fields = "__all__"

