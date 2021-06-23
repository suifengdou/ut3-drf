from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import CompanySerializer
from .filters import CompanyFilter
from .models import Company
from ut3.permissions import Permissions


class CompanyViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定公司
    list:
        返回公司列表
    update:
        更新公司信息
    destroy:
        删除公司信息
    create:
        创建公司信息
    partial_update:
        更新部分公司字段
    """
    queryset = Company.objects.all().order_by("id")
    serializer_class = CompanySerializer
    filter_class = CompanyFilter
    filter_fields = ("name", "company", "tax_fil_number", "order_status", "category", "spain_invoice",
                     "special_invoice", "discount_rate", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['company.view_company']
    }