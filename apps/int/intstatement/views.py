import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np

import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict

from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import IntStatement
from .serializers import IntStatementSerializer
from .filters import IntStatementFilter
from apps.utils.geography.models import City, District
from apps.int.intaccount.models import IntAccount, Currency
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from ut3.settings import EXPORT_TOPLIMIT


class IntStatementRelatedViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定结算单
    list:
        返回结算单明细
    update:
        更新结算单明细
    destroy:
        删除结算单明细
    create:
        创建结算单明细
    partial_update:
        更新部分结算单明细
    """
    serializer_class = IntStatementSerializer
    filter_class = IntStatementFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['intpurchase.view_intpurchaseorder',]
    }

    def get_queryset(self):
        if not self.request:
            return IntStatement.objects.none()
        queryset = IntStatement.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["creator"] = user.username
        params["order_status"] = 1
        f = IntStatementFilter(params)
        serializer = IntStatementSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        user = self.request.user
        params["creator"] = user.username
        if all_select_tag:
            handle_list = IntStatementFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntStatement.objects.filter(id__in=order_ids, order_status=1, creator=user.username)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
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
                if obj.amount == 0:
                    data["error"].append("%s收款金额为0" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue

                obj.remaining = obj.amount

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
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
            raise serializers.ValidationError("没有可取消的单据！")
        data["successful"] = n
        return Response(data)

class IntStatementManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定结算单
    list:
        返回结算单明细
    update:
        更新结算单明细
    destroy:
        删除结算单明细
    create:
        创建结算单明细
    partial_update:
        更新部分结算单明细
    """
    serializer_class = IntStatementSerializer
    filter_class = IntStatementFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['intpurchase.view_intpurchaseorder',]
    }

    def get_queryset(self):
        if not self.request:
            return IntStatement.objects.none()
        queryset = IntStatement.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["creator"] = user.username
        params["order_status"] = 1
        f = IntReceiptFilter(params)
        serializer = IntReceiptSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        user = self.request.user
        params["creator"] = user.username
        if all_select_tag:
            handle_list = IntStatementFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = IntStatement.objects.filter(id__in=order_ids, order_status=1, creator=user.username)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
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
                if obj.amount == 0:
                    data["error"].append("%s收款金额为0" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue

                obj.remaining = obj.amount

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
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
            raise serializers.ValidationError("没有可取消的单据！")
        data["successful"] = n
        return Response(data)


