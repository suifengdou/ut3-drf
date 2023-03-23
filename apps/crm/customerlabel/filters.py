# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm
from django.db.models import F, Q

import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import CustomerLabelPerson, LogCustomerLabelPerson, CustomerLabelFamily, LogCustomerLabelFamily, \
    CustomerLabelProduct, LogCustomerLabelProduct, CustomerLabelOrder, LogCustomerLabelOrder, CustomerLabelService, \
    LogCustomerLabelService, CustomerLabelSatisfaction, LogCustomerLabelSatisfaction, CustomerLabelRefund, \
    LogCustomerLabelRefund, CustomerLabelOthers, LogCustomerLabelOthers
from apps.utils.orm.queryfunc import andconmbine


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class CustomerLabelPersonFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelPerson
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelFamilyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelFamily
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelProduct
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelOrderFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelOrder
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelServiceFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelService
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelSatisfactionFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelSatisfaction
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelRefundFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelRefund
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


class CustomerLabelOthersFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    name__in = CharInFilter(field_name='name', lookup_expr='in')
    labelcustomer__label__name = django_filters.CharFilter(method='clabel_filter')

    class Meta:
        model = CustomerLabelOthers
        fields = "__all__"

    def __init__(self, *args, author=None, **kwargs):
        super().__init__(*args, **kwargs)
        # do something w/ author

    def clabel_filter(self, queryset, name, *value):
        name = '%s__icontains' % name
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _condition_dict = {}
            for value in condition_list:
                _condition_dict[name] = value
                queryset = queryset.filter(**_condition_dict)
        return queryset


