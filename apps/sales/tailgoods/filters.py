# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import OriTailOrder, OTOGoods, TailOrder, TOGoods, RefundOrder, ROGoods, PayBillOrder, PBOGoods, \
    ArrearsBillOrder, ABOGoods, FinalStatement, FinalStatementGoods, AccountInfo, PBillToAccount, ABillToAccount, \
    TailToExpense, RefundToPrestore


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class OriTailOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OriTailOrder
        fields = "__all__"


class OTOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = OTOGoods
        fields = "__all__"


class TailOrderFilter(django_filters.FilterSet):
    ori_tail_order__order_id = django_filters.CharFilter(lookup_expr='exact')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()
    update_time = django_filters.DateTimeFromToRangeFilter()
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")

    class Meta:
        model = TailOrder
        fields = "__all__"


class TOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    tail_order__order_id = django_filters.CharFilter(lookup_expr='iexact')
    tail_order__sent_consignee = django_filters.CharFilter(lookup_expr='icontains')
    tail_order__sent_smartphone = django_filters.CharFilter(lookup_expr='icontains')
    tail_order__order_status = django_filters.NumberFilter(lookup_expr='exact')
    tail_order__mode_warehouse = django_filters.NumberFilter(lookup_expr='exact')
    tail_order__track_no = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = TOGoods
        fields = "__all__"


class RefundOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    handle_time = django_filters.DateTimeFromToRangeFilter()
    create_time = django_filters.DateTimeFromToRangeFilter()
    track_no__in = CharInFilter(field_name="track_no", lookup_expr="in")

    class Meta:
        model = RefundOrder
        fields = "__all__"


class ROGoodsFilter(django_filters.FilterSet):
    refund_order__track_no = django_filters.CharFilter(lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ROGoods
        fields = "__all__"


class PayBillOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = PayBillOrder
        fields = "__all__"


class PBOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = PBOGoods
        fields = "__all__"


class ArrearsBillOrderFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ArrearsBillOrder
        fields = "__all__"


class ABOGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ABOGoods
        fields = "__all__"


class FinalStatementFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = FinalStatement
        fields = "__all__"


class FinalStatementGoodsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = FinalStatementGoods
        fields = "__all__"


class AccountInfoFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = AccountInfo
        fields = "__all__"


class PBillToAccountFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = PBillToAccount
        fields = "__all__"


class ABillToAccountFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = ABillToAccount
        fields = "__all__"


class TailToExpenseFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = TailToExpense
        fields = "__all__"

class RefundToPrestoreFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = RefundToPrestore
        fields = "__all__"












