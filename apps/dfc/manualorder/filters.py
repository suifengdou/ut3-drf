# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import OriTailOrder, OTOGoods, TailOrder, TOGoods, RefundOrder, ROGoods, PayBillOrder, PBOGoods, \
    ArrearsBillOrder, ABOGoods, FinalStatement, FinalStatementGoods, AccountInfo, PBillToAccount, ABillToAccount, \
    TailPartsOrder, TailToExpense, RefundToPrestore


class OriTailOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OriTailOrder
        fields = "__all__"












