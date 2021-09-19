from django.shortcuts import render
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from .filters import UserFilter
from ut3.permissions import Permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from django.contrib.auth import authenticate

User = get_user_model()

class UserViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定用户
    list:
        返回用户列表
    update:
        更新用户信息
    destroy:
        删除用户信息
    create:
        创建用户信息
    partial_update:
        更新部分用户字段
    """
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    filter_class = UserFilter
    filter_fields = ("username", "creator", "create_time", "is_staff", "is_active")
    permission_classes = (IsAuthenticated,)
    extra_perm_map = {
        "GET": ['users.view_userprofile']
    }

    def list(self, request, *args, **kwargs):
        print(request)
        return super(UserViewset, self).list(request, *args, **kwargs)

    @action(methods=["get"], detail=False)
    def get_user_info(self, request, *args, **kwargs):
        user = request.user
        error = {"id": -1, "name": "错误"}
        try:
            company = {
                "id": user.company.id,
                "name": user.company.name
            }
        except:
            company = error
        try:
            department = {
                "id": user.department.id,
                "name": user.department.name
            }

        except:
            department = error
        if user.is_superuser:
            roles = ["AllPrivileges"]
        else:
            result_permissions = filter(lambda x: "view" in x, user.get_group_permissions())
            roles = list(result_permissions)
        data = {
            "name": user.username,
            "roles": roles,
            "avatar": 'http://qy9qcmykj.hb-bkt.clouddn.com/avatar-male.png',
            "introduction": "UT3用户",
            "company": company,
            "department": department
        }
        return response.Response(data)

    @action(methods=["patch"], detail=False)
    def reset_password(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        if data["new_password"] != data["pwd_repeat"]:
            raise serializers.ValidationError("新密码和确认密码不一致！")
        if len(data["new_password"]) < 5 or len(data["new_password"]) > 15:
            raise serializers.ValidationError("新密码最少5位，最大14位！")
        check_user = authenticate(username=user.username, password=data["password"])
        if user == check_user:
            user.set_password(data["new_password"])
            user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            raise serializers.ValidationError("原密码错误！")


class DashboardViewset(viewsets.ViewSet, mixins.ListModelMixin):
    permission_classes = (IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        data = {
            "card1": {
                "cck": 2,
                "ccm": 3
            },
            "ppc": "ok"
        }
        return response.Response(data)

