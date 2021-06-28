# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import ExpressWorkOrder

class ExpressWorkOrderFilter(django_filters.FilterSet):

    class Meta:
        model = ExpressWorkOrder
        fields = "__all__"

