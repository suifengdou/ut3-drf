from django.shortcuts import render
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer, UserPasswordSerializer
from .filters import UserFilter
from ut3.permissions import Permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import action

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
        print(user.get_all_permissions())
        company = {
            "id": user.company.id,
            "name": user.company.name
        }
        department = {
            "id": user.department.id,
            "name": user.department.name
        }
        if user.is_superuser:
            roles = ["AllPrivileges"]
        else:
            result_permissions = filter(lambda x: "view" in x, user.get_all_permissions())
            roles = list(result_permissions)
        data = {
            "name": user.username,
            "roles": roles,
            "avatar": 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
            "introduction": "UT3用户",
            "company": company,
            "department": department
        }
        return response.Response(data)

class UserPasswordViewset(viewsets.GenericViewSet,
                          mixins.UpdateModelMixin):
    queryset = User.objects.all()
    serializer_class = UserPasswordSerializer


class UserAction(viewsets.ViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def list(self, request, *args, **kwargs):
        print(request)
        data = {
            "id": "1",
            "name": "mmk",
            "roles": "admin"
        }
        return response.Response(data)

    def create(self, request, *args, **kwargs):
        print(request)
        data = {
            "id": "1",
            "name": "mmk",
            "roles": "admin"
        }
        return response.Response(data)

    @action(methods=['post'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        data = {
            "id": "1",
            "name": "mmk",
            "roles": "admin"
        }
        return response.Response(data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)



    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)