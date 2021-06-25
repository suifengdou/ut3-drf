# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import DealerWorkOrder

class DealerWorkOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')

    class Meta:
        model = DealerWorkOrder
        fields = "__all__"

