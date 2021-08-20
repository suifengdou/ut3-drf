from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import NationalitySerializer, ProvinceSerializer, CitySerializer, DistrictSerializer
from .filters import NationalityFilter, ProvinceFilter, CityFilter, DistrictFilter
from .models import Nationality, Province, City, District
from ut3.permissions import Permissions


class NationalityViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定国籍
    list:
        返回国籍列表
    update:
        更新国籍信息
    destroy:
        删除国籍信息
    create:
        创建国籍信息
    partial_update:
        更新部分国籍字段
    """
    queryset = Nationality.objects.all().order_by("id")
    serializer_class = NationalitySerializer
    filter_class = NationalityFilter
    filter_fields =  "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['geography.view_nationality']
    }


class ProvinceViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定省份
    list:
        返回省份列表
    update:
        更新省份信息
    destroy:
        删除省份信息
    create:
        创建省份信息
    partial_update:
        更新部分省份字段
    """
    queryset = Province.objects.all().order_by("id")
    serializer_class = ProvinceSerializer
    filter_class = ProvinceFilter
    filter_fields =  "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['geography.view_nationality']
    }

class CityViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定城市
    list:
        返回城市列表
    update:
        更新城市信息
    destroy:
        删除城市信息
    create:
        创建城市信息
    partial_update:
        更新部分城市字段
    """
    queryset = City.objects.all().order_by("id")
    serializer_class = CitySerializer
    filter_class = CityFilter
    filter_fields =  "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['geography.view_city']
    }


class DistrictViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定区县
    list:
        返回区县列表
    update:
        更新区县信息
    destroy:
        删除区县信息
    create:
        创建区县信息
    partial_update:
        更新部分区县字段
    """
    queryset = District.objects.all().order_by("id")
    serializer_class = DistrictSerializer
    filter_class = DistrictFilter
    filter_fields =  "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['geography.view_district']
    }