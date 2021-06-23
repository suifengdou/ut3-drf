# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import OriInvoice, OriInvoiceGoods, Invoice, InvoiceGoods, DeliverOrder

class OriInvoiceFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OriInvoice
        fields = "__all__"


class OriInvoiceGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OriInvoiceGoods
        fields = "__all__"


class InvoiceFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    work_order = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=OriInvoice.objects.all())

    class Meta:
        model = Invoice
        fields = "__all__"


class InvoiceGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = InvoiceGoods
        fields = "__all__"


class DeliverOrderFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = DeliverOrder
        fields = "__all__"