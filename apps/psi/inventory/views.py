import re, datetime
import math
import pandas as pd
import numpy as np
from django.db.models import Avg, Sum, Max, Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import InventorySerializer
from .filters import InventoryFilter
from .models import Inventory
from apps.sales.advancepayment.models import Expense, Account, Statements, VerificationExpenses, ExpendList, Prestore
from apps.auth.users.models import UserProfile
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from ut3.settings import EXPORT_TOPLIMIT


class InventoryViewset(viewsets.ModelViewSet):
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
    serializer_class = InventorySerializer
    filter_class = InventoryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return Inventory.objects.none()
        user = self.request.user
        queryset = Inventory.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = InventoryFilter(params)
        serializer = InventorySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = InventoryFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Inventory.objects.filter(id__in=order_ids, order_status=1)
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
        try:
            account = request.user.account
        except:
            raise serializers.ValidationError("不存在预存账户！")
        all_prestores = account.prestore_set.filter(order_status=3)
        if all_prestores:
            balance = all_prestores.aggregate(Sum("remaining"))["remaining__sum"]
        else:
            raise serializers.ValidationError("账户无余额！")
        if not account.order_status:
            raise serializers.ValidationError("账户被冻结！")
        try:
            company = check_list[0].shop.company
        except Exception as e:
            raise serializers.ValidationError("店铺未关联公司！")

        if n:
            for obj in check_list:

                check_fields = ['order_id', 'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address']
                for key in check_fields:
                    value = getattr(obj, key, None)
                    if value:
                        setattr(obj, key, str(value).replace(' ', '').replace("'", '').replace('\n', ''))

                if not obj.sign_company:
                    data["error"].append("%s 账号没有设置公司" % obj.order_id)
                    obj.mistake_tag = 1
                    obj.save()
                    n -= 1
                    continue
                _q_repeated_order = Inventory.objects.filter(sent_consignee=obj.sent_consignee,
                                                             order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
                        obj.save()
                        n -= 1
                        continue
                _q_repeated_order = Inventory.objects.filter(sent_smartphone=obj.sent_smartphone,
                                                             order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
                        obj.save()
                        n -= 1
                        continue

                if obj.amount <= 0:
                    data["error"].append("%s 没添加货品, 或者货品价格添加错误" % obj.order_id)
                    obj.mistake_tag = 2
                    obj.save()
                    n -= 1
                    continue
                # 判断专票信息是否完整
                if not re.match(r'^[0-9-]+$', obj.sent_smartphone):
                    data["error"].append("%s 收件人手机错误" % obj.order_id)
                    obj.mistake_tag = 3
                    obj.save()
                    n -= 1
                    continue
                if not re.match("^[0-9A-Za-z]+$", obj.order_id):
                    data["error"].append("%s 单号只支持数字和英文字母" % obj.order_id)
                    obj.mistake_tag = 4
                    obj.save()
                    n -= 1
                    continue
                if obj.process_tag != 10:
                    if obj.mode_warehouse:

                        if obj.process_tag != 8:
                            data["error"].append("%s 发货仓库和单据类型不符" % obj.order_id)
                            obj.mistake_tag = 12
                            obj.save()
                            n -= 1
                            continue
                    else:
                        if obj.process_tag != 9:
                            data["error"].append("%s 发货仓库和单据类型不符" % obj.order_id)
                            obj.mistake_tag = 12
                            obj.save()
                            n -= 1
                            continue
                check_name = obj.goods_name()
                if check_name not in ['无', '多种']:
                    check_name = check_name.lower().replace(' ', '')
                    if check_name not in str(obj.message):
                        data["error"].append("%s 发货型号与备注不符" % obj.order_id)
                        obj.mistake_tag = 16
                        obj.save()
                        n -= 1
                        continue
                obj.submit_time = datetime.datetime.now()
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
    def set_used(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=8)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
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
