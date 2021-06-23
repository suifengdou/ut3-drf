# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Company

class CompanyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    tax_fil_number = django_filters.CharFilter(field_name="tax_fil_number", lookup_expr='icontains')

    class Meta:
        model = Company
        fields = ["name", "company", "tax_fil_number", "order_status", "category", "spain_invoice",
                  "special_invoice", "discount_rate", "create_time", "update_time", "is_delete", "creator"]