# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 9:27
# @Author  : Hann
# @Site    : 
# @File    : filters.py
# @Software: PyCharm

import django_filters
from .models import Nationality, Province, City, District

class NationalityFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')

    class Meta:
        model = Nationality
        fields = "__all__"


class ProvinceFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    nationality = django_filters.ModelChoiceFilter(to_field_name="id", queryset=Nationality.objects.all())

    class Meta:
        model = Province
        fields ="__all__"


class CityFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    nationality = django_filters.ModelChoiceFilter(to_field_name="id", queryset=Nationality.objects.all())
    province = django_filters.ModelChoiceFilter(to_field_name="id", queryset=Province.objects.all())

    class Meta:
        model = City
        fields = "__all__"


class DistrictFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains')
    nationality = django_filters.ModelChoiceFilter(to_field_name="id", queryset=Nationality.objects.all())
    province = django_filters.ModelChoiceFilter(to_field_name="id", queryset=Province.objects.all())
    city = django_filters.ModelChoiceFilter(to_field_name="id", queryset=City.objects.all())

    class Meta:
        model = District
        fields = "__all__"