import pandas as pd
import numpy as np
import datetime
import re
from functools import reduce
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import AccountSerializer, StatementsSerializer, PrestoreSerializer, ExpenseSerializer, \
    VerificationPrestoreSerializer, VerificationExpensesSerializer, ExpendListSerializer
from .models import Account, Statements, Prestore, Expense, VerificationPrestore, VerificationExpenses, ExpendList
from .filters import AccountFilter, StatementsFilter, PrestoreFilter, ExpenseFilter, VerificationPrestoreFilter, \
    VerificationExpensesFilter, ExpendListFilter
from ut3.permissions import Permissions
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.decorators import action


class AccountViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    queryset = Account.objects.all().order_by("id")
    serializer_class = AccountSerializer
    filter_class = AccountFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = AccountFilter(params)
        serializer = AccountSerializer(f.qs, many=True)
        return Response(serializer.data)


class MyAccountViewset(viewsets.ReadOnlyModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = AccountSerializer
    filter_class = AccountFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Account.objects.none()
        user = self.request.user
        queryset = Account.objects.filter(user=user).order_by("id")
        return queryset


class StatementsViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = StatementsSerializer
    filter_class = StatementsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Statements.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = Statements.objects.all().order_by("id")
        else:
            queryset = Statements.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = StatementsFilter(params)
        serializer = StatementsSerializer(f.qs, many=True)
        return Response(serializer.data)



class PrestoreSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = PrestoreSerializer
    filter_class = PrestoreFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Prestore.objects.none()
        user = self.request.user
        queryset = Prestore.objects.filter(creator=user.username, order_status=1, category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = PrestoreFilter(params)
        serializer = PrestoreSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = PrestoreFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Prestore.objects.filter(id__in=order_ids, order_status=1)
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
            for order in check_list:
                if order.amount <= 0:
                    order.mistake_tag = 1
                    data["error"].append("%s 预存单金额错误" % order.order_id)
                    order.save()
                    n -= 1
                    continue
                order.order_status = 2
                order.mistake_tag = 0
                order.save()
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
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class PrestoreCheckViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = PrestoreSerializer
    filter_class = PrestoreFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Prestore.objects.none()
        queryset = Prestore.objects.filter(order_status=2, category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = PrestoreFilter(params)
        serializer = PrestoreSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = PrestoreFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Prestore.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        user = request.user.username
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:
                if order.amount <= 0:
                    order.mistake_tag = 1
                    data["error"].append("%s 预存单金额错误" % order.order_id)
                    order.save()
                    n -= 1
                    continue
                _q_verifyprestore = VerificationPrestore.objects.filter(prestore=order)
                if _q_verifyprestore:
                    order.mistake_tag = 3
                    data["error"].append("%s 预存单不可重复审核" % order.order_id)
                    order.save()
                    n -= 1
                    continue
                statement = Statements()
                statement.order_id = 'SN' + str(order.order_id)
                statement.revenue = order.amount
                statement.category = order.category
                statement.account = order.account
                statement.creator = user
                try:
                    statement.save()
                except Exception as e:
                    order.mistake_tag = 4
                    data["error"].append("%s 保存流水出错 %s " % (order.order_id, e))
                    order.save()
                    n -= 1
                    continue
                verifyprestore = VerificationPrestore()
                verifyprestore.prestore = order
                verifyprestore.statement = statement
                verifyprestore.creator = user
                try:
                    verifyprestore.save()
                except Exception as e:
                    order.mistake_tag = 5
                    data["error"].append("%s 保存验证出错 %s " % (order.order_id, e))
                    order.save()
                    n -= 1
                    continue
                order.remaining = order.amount
                order.order_status = 3
                order.mistake_tag = 0
                order.save()
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
            for order in reject_list:
                if not order.feedback:
                    data["error"].append("%s 驳回时，反馈内容必填！")
                    order.mistake_tag = 2
                    order.save()
                    n -= 1
                else:
                    order.mistake_tag = 0
                    order.order_status = 1
                    order.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)


class PrestoreManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = PrestoreSerializer
    filter_class = PrestoreFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Prestore.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = Prestore.objects.all().order_by("id")
        else:
            queryset = Prestore.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = PrestoreFilter(params)
        serializer = PrestoreSerializer(f.qs, many=True)
        return Response(serializer.data)


class ExpenseViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = ExpenseSerializer
    filter_class = ExpenseFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Expense.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = Expense.objects.all().order_by("id")
        else:
            queryset = Expense.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpenseFilter(params)
        serializer = ExpenseSerializer(f.qs, many=True)
        return Response(serializer.data)


class VerificationPrestoreViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = VerificationPrestoreSerializer
    filter_class = VerificationPrestoreFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return VerificationPrestore.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = VerificationPrestore.objects.all().order_by("id")
        else:
            queryset = VerificationPrestore.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = VerificationPrestoreFilter(params)
        serializer = VerificationPrestoreSerializer(f.qs, many=True)
        return Response(serializer.data)


class VerificationExpensesViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = VerificationExpensesSerializer
    filter_class = VerificationExpensesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return VerificationExpenses.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = VerificationExpenses.objects.all().order_by("id")
        else:
            queryset = VerificationExpenses.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = VerificationExpensesFilter(params)
        serializer = VerificationExpensesSerializer(f.qs, many=True)
        return Response(serializer.data)


class ExpendListViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = ExpendListSerializer
    filter_class = ExpendListFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpendList.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = ExpendList.objects.all().order_by("id")
        else:
            queryset = ExpendList.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpendListFilter(params)
        serializer = ExpendListSerializer(f.qs, many=True)
        return Response(serializer.data)

