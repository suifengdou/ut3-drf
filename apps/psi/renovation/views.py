import re, datetime
import math
import pandas as pd
import numpy as np
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import RenovationSerializer, RenovationGoodsSerializer, RenovationdetailSerializer
from .filters import RenovationFilter, RenovationGoodsFilter, RenovationdetailFilter
from .models import Renovation, RenovationGoods, Renovationdetail, LogRenovation, LogRenovationGoods, LogRenovationdetail
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.psi.inventory.models import Inventory
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.utils.logging.loggings import getlogs, logging
from ut3.settings import EXPORT_TOPLIMIT


class RenovationSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationSerializer
    filter_class = RenovationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovation.objects.none()
        user = self.request.user
        queryset = Renovation.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        f = RenovationFilter(params)
        serializer = RenovationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = RenovationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Renovation.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                all_goods_details = obj.inbounddetail_set.filter(order_status=1)
                if not all_goods_details.exists():
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                obj.order_status = 2
                for goods in all_goods_details:
                    goods.order_status = 2
                    goods.save()
                    logging(goods, user, LogRenovation, "提交")
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogRenovation, "提交")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_retread(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=9)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=10)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def recover(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=0)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class RenovationManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationSerializer
    filter_class = RenovationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovation.objects.none()
        user = self.request.user
        queryset = Renovation.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationFilter(params)
        serializer = RenovationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovation)
        return Response(ret)


class RenovationGoodsManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationGoodsSerializer
    filter_class = RenovationGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return RenovationGoods.objects.none()
        user = self.request.user
        queryset = RenovationGoods.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationGoodsFilter(params)
        serializer = RenovationGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = RenovationGoods.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovationGoods)
        return Response(ret)


class RenovationdetailManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationdetailSerializer
    filter_class = RenovationdetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovationdetail.objects.none()
        user = self.request.user
        queryset = Renovationdetail.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationdetailFilter(params)
        serializer = RenovationdetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovationdetail.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovationdetail)
        return Response(ret)

































