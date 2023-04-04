# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Account, Statements, Prestore, Expense, VerificationPrestore, VerificationExpenses, ExpendList

class AccountFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Account
        fields = "__all__"


class StatementsFilter(django_filters.FilterSet):
    account__name = django_filters.CharFilter(lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Statements
        fields = "__all__"


class PrestoreFilter(django_filters.FilterSet):
    account__name = django_filters.CharFilter(lookup_expr='icontains')
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    bank_sn = django_filters.CharFilter(field_name="bank_sn", lookup_expr='icontains')
    memorandum = django_filters.CharFilter(field_name="memorandum", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()


    class Meta:
        model = Prestore
        fields = "__all__"


class ExpenseFilter(django_filters.FilterSet):
    memorandum = django_filters.CharFilter(field_name="memorandum", lookup_expr='icontains')
    created_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Expense
        fields = "__all__"


class VerificationPrestoreFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    prestore__order_id = django_filters.CharFilter(lookup_expr='icontains')
    statement__order_id = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = VerificationPrestore
        fields = "__all__"


class VerificationExpensesFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    expense__order_id = django_filters.CharFilter(lookup_expr='icontains')
    statement__order_id = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = VerificationExpenses
        fields = "__all__"


class ExpendListFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    prestore__order_id = django_filters.CharFilter(lookup_expr='icontains')
    statements__order_id = django_filters.CharFilter(lookup_expr='icontains')
    account__name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ExpendList
        fields = "__all__"