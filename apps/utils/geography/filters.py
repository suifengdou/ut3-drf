# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Nationality, Province, City, District

class NationalityFilter(django_filters.FilterSet):
    nationality = django_filters.CharFilter(field_name="nationality", lookup_expr='icontains')

    class Meta:
        model = Nationality
        fields = ["nationality", "abbreviation", "area_code", "create_time", "update_time",
                  "is_delete", "creator"]


class ProvinceFilter(django_filters.FilterSet):
    province = django_filters.CharFilter(field_name="province", lookup_expr='icontains')

    class Meta:
        model = Province
        fields = ["nationality", "province", "area_code", "create_time", "update_time", "is_delete", "creator"]


class CityFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="city", lookup_expr='icontains')

    class Meta:
        model = City
        fields = ["nationality", "province", "city", "area_code", "create_time", "update_time",
                  "is_delete", "creator"]


class DistrictFilter(django_filters.FilterSet):
    district = django_filters.CharFilter(field_name="district", lookup_expr='icontains')

    class Meta:
        model = District
        fields = ["nationality", "province", "city", "district", "create_time", "update_time",
                  "is_delete", "creator"]