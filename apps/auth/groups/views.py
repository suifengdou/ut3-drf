from rest_framework import viewsets
from django.contrib.auth.models import Group
from .serializers import GroupSerializer, PermissionSerializer
from .filter import GroupFilter, PermissionFilter
from ut3.permissions import Permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth.models import Permission


class GroupViewset(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("id")
    serializer_class = GroupSerializer
    filter_class = GroupFilter
    filter_fields = ("name",)
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['auth.view_group']
    }


class PermissionViewset(viewsets.ModelViewSet):
    queryset = Permission.objects.all().order_by("id")
    serializer_class = PermissionSerializer
    filter_class = PermissionFilter
    filter_fields = ("name",)
    permission_classes = (IsAdminUser, Permissions)





