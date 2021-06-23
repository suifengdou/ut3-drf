# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Goods, GoodsCategory

class GoodsFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    goods_id = django_filters.CharFilter(field_name="name", lookup_expr='exact')

    class Meta:
        model = Goods
        fields = ["goods_id", "name", "category", "goods_attribute", "goods_number",
                  "size", "width", "height", "depth", "weight", "catalog_num", "create_time",
                  "update_time", "is_delete", "creator"]


class GoodsCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    code = django_filters.CharFilter(field_name="code", lookup_expr='icontains')

    class Meta:
        model = GoodsCategory
        fields = ["name", "code", "create_time", "update_time", "is_delete", "creator"]