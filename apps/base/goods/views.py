from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import GoodsCategorySerializer, GoodsSerializer
from .filters import GoodsFilter, GoodsCategoryFilter
from .models import GoodsCategory, Goods
from ut3.permissions import Permissions


class GoodsViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品
    list:
        返回货品列表
    update:
        更新货品信息
    destroy:
        删除货品信息
    create:
        创建货品信息
    partial_update:
        更新部分货品字段
    """
    queryset = Goods.objects.all().order_by("id")
    serializer_class = GoodsSerializer
    filter_class = GoodsFilter
    filter_fields = ("goods_id", "name", "category", "goods_attribute", "goods_number",
                     "size", "width", "height", "depth", "weight", "catalog_num", "create_time",
                     "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }


class GoodsCategoryViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品类别
    list:
        返回货品类别列表
    update:
        更新货品类别信息
    destroy:
        删除货品类别信息
    create:
        创建货品类别信息
    partial_update:
        更新部分货品类别字段
    """
    queryset = GoodsCategory.objects.all().order_by("id")
    serializer_class = GoodsCategorySerializer
    filter_class = GoodsCategoryFilter
    filter_fields = ("name", "code", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }
