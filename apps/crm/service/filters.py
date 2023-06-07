# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import datetime
import django_filters
from django_filters.filters import BaseInFilter, NumberFilter, CharFilter
from .models import OriMaintenance, Maintenance, MaintenanceSummary, OriMaintenanceGoods, MaintenanceGoods, MaintenancePartSummary


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


class OriMaintenanceFilter(django_filters.FilterSet):
    process_tag = django_filters.CharFilter(method='multiple_filter')
    mistake_tag = django_filters.CharFilter(method='multiple_filter')
    sign = django_filters.CharFilter(method='multiple_filter')
    created_time = django_filters.DateTimeFromToRangeFilter()
    purchase_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    ori_created_time = django_filters.DateTimeFromToRangeFilter()
    finish_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(method='order_id_filter')

    class Meta:
        model = OriMaintenance
        fields = "__all__"

    def order_id_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset

    def multiple_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset


class MaintenanceFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    handle_time = django_filters.DateTimeFromToRangeFilter()
    ori_create_time = django_filters.DateTimeFromToRangeFilter()
    finish_time = django_filters.DateTimeFromToRangeFilter()
    order_id = django_filters.CharFilter(method='order_id_filter')
    order_status__in = NumberInFilter(field_name="order_status", lookup_expr="in")
    process_tag__in = NumberInFilter(field_name="process_tag", lookup_expr="in")
    fault_cause__in = NumberInFilter(field_name="fault_cause", lookup_expr="in")

    class Meta:
        model = Maintenance
        fields = "__all__"

    def order_id_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset


class MaintenanceSummaryFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    summary_date_range = django_filters.CharFilter(method='date_filter')

    class Meta:
        model = MaintenanceSummary
        fields = "__all__"

    def date_filter(self, queryset, name, *value):
        name = name.replace("_range", "")
        condition_list = str(value[0]).split(",")
        if len(condition_list) == 2:
            condition_dict = {
                f"{name}__gte": datetime.datetime.strptime(condition_list[0], "%Y-%m-%d %H:%M:%S"),
                f"{name}__lte": datetime.datetime.strptime(condition_list[1], "%Y-%m-%d %H:%M:%S")
            }
            check_days = condition_dict[ f"{name}__lte"] - condition_dict[ f"{name}__gte"]
            if check_days.days > 120:
                condition_dict[f"{name}__lte"] = condition_dict[f"{name}__gte"] + datetime.timedelta(days=120)
            queryset = queryset.filter(**condition_dict)
        else:
            queryset = queryset.filter(**{name: datetime.datetime.now()})

        return queryset


class OriMaintenanceGoodsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    finish_time_range = django_filters.CharFilter(method='date_filter')
    order_id = django_filters.CharFilter(method='order_id_filter')

    class Meta:
        model = OriMaintenanceGoods
        fields = "__all__"

    def order_id_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset

    def date_filter(self, queryset, name, *value):
        name = name.replace("_range", "")
        condition_list = str(value[0]).split(",")
        if len(condition_list) == 2:
            condition_dict = {
                f"{name}__gte": datetime.datetime.strptime(condition_list[0], "%Y-%m-%d %H:%M:%S"),
                f"{name}__lte": datetime.datetime.strptime(condition_list[1], "%Y-%m-%d %H:%M:%S")
            }
            check_days = condition_dict[ f"{name}__lte"] - condition_dict[ f"{name}__gte"]
            if check_days.days > 120:
                condition_dict[f"{name}__lte"] = condition_dict[f"{name}__gte"] + datetime.timedelta(days=120)
            queryset = queryset.filter(**condition_dict)
        else:
            queryset = queryset.filter(**{name: datetime.datetime.now()})

        return queryset


class MaintenanceGoodsFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    order__order_id = django_filters.CharFilter(method='order_id_filter')
    part__name = django_filters.CharFilter(method='part_filter')

    class Meta:
        model = MaintenanceGoods
        fields = "__all__"

    def order_id_filter(self, queryset, name, *value):
        condition_list = str(value[0]).split()
        if len(condition_list) == 1:
            queryset = queryset.filter(**{name: condition_list[0]})
        else:
            _temp_queryset = None
            for value in condition_list:
                if _temp_queryset:
                    _temp_queryset = _temp_queryset | queryset.filter(**{name: value})
                else:
                    _temp_queryset = queryset.filter(**{name: value})
            queryset = _temp_queryset
        return queryset

    def part_filter(self, queryset, name, *value):
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


class MaintenancePartSummaryFilter(django_filters.FilterSet):
    created_time = django_filters.DateTimeFromToRangeFilter()
    summary_date_range = django_filters.CharFilter(method='date_filter')

    class Meta:
        model = MaintenancePartSummary
        fields = "__all__"

    def date_filter(self, queryset, name, *value):
        name = name.replace("_range", "")
        condition_list = str(value[0]).split(",")
        if len(condition_list) == 2:
            condition_dict = {
                f"{name}__gte": datetime.datetime.strptime(condition_list[0], "%Y-%m-%d %H:%M:%S"),
                f"{name}__lte": datetime.datetime.strptime(condition_list[1], "%Y-%m-%d %H:%M:%S")
            }
            check_days = condition_dict[ f"{name}__lte"] - condition_dict[ f"{name}__gte"]
            if check_days.days > 120:
                condition_dict[f"{name}__lte"] = condition_dict[f"{name}__gte"] + datetime.timedelta(days=120)
            queryset = queryset.filter(**condition_dict)
        else:
            queryset = queryset.filter(**{name: datetime.datetime.now()})

        return queryset

