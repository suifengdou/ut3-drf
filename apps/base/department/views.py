from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import DepartmentSerializer, CenterSerializer
from .filters import DepartmentFilter, CenterFilter
from .models import Department, Center
from ut3.permissions import Permissions


class CenterViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定中心
    list:
        返回中心列表
    update:
        更新中心信息
    destroy:
        删除中心信息
    create:
        创建中心信息
    partial_update:
        更新部分中心字段
    """
    queryset = Center.objects.all().order_by("id")
    serializer_class = CenterSerializer
    filter_class = CenterFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['department.view_department']
    }

class DepartmentViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定部门
    list:
        返回部门列表
    update:
        更新部门信息
    destroy:
        删除部门信息
    create:
        创建部门信息
    partial_update:
        更新部分部门字段
    """
    queryset = Department.objects.all().order_by("id")
    serializer_class = DepartmentSerializer
    filter_class = DepartmentFilter
    filter_fields = ("name", "d_id", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['department.view_department']
    }