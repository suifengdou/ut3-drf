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
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Account
        fields = "__all__"


class StatementsFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Statements
        fields = "__all__"


class PrestoreFilter(django_filters.FilterSet):
    order_id = django_filters.CharFilter(field_name="order_id", lookup_expr='icontains')
    create_time = django_filters.DateTimeFromToRangeFilter()


    class Meta:
        model = Prestore
        fields = "__all__"


class ExpenseFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = Expense
        fields = "__all__"


class VerificationPrestoreFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    prestore = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Prestore.objects.all())
    statement = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Statements.objects.all())

    class Meta:
        model = VerificationPrestore
        fields = "__all__"


class VerificationExpensesFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    expense = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Expense.objects.all())
    statement = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Statements.objects.all())

    class Meta:
        model = VerificationExpenses
        fields = "__all__"


class ExpendListFilter(django_filters.FilterSet):
    create_time = django_filters.DateTimeFromToRangeFilter()
    prestore = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Prestore.objects.all())
    statement = django_filters.ModelChoiceFilter(to_field_name="order_id", queryset=Statements.objects.all())

    class Meta:
        model = ExpendList
        fields = "__all__"