import re
import datetime
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import ExpressWorkOrder
from .serializers import ExpressWorkOrderSerializer
from .filters import ExpressWorkOrderFilter


class EWOReverseCreateViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        queryset = ExpressWorkOrder.objects.filter(company=user.company, order_status=1,  wo_category=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["wo_category"] = 1
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:
                if not re.match(r'^[SF0-9]+$', order.track_id):
                    data["error"].append("%s 快递单号错误" % order.track_id)
                    n -= 1
                    continue
                if order.is_losing and order.is_return:
                    data["error"].append("%s 丢件和返回不可同时存在！" % order.track_id)
                    n -= 1
                    continue
                if any([order.is_return, order.return_express_id]):
                    if not all([order.is_return, order.return_express_id]):
                        data["error"].append("%s 返回时，返回单号必填，或者有返回单号，必须确认返回项！" % order.track_id)
                        n -= 1
                        continue
                order.order_status = 2
                order.mistake_tag = 0
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)


class EWOCreateViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        queryset = ExpressWorkOrder.objects.filter(company=user.company, order_status=1, wo_category=0).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["wo_category"] = 0
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:
                if not re.match(r'^[SF0-9]+$', order.track_id):
                    data["error"].append("%s 快递单号错误" % order.track_id)
                    n -= 1
                    continue
                order.servicer = request.user.username
                order.submit_time = datetime.datetime.now()
                order.order_status = 2
                order.mid_handler = 3
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)


class EWOHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        queryset = ExpressWorkOrder.objects.filter(order_status=2, wo_category=1, mid_handler__in=[0, 1, 2]).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        params["wo_category"] = 1
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["wo_category"] = 1
        params["mid_handler__in"] = '0, 1, 2'
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=2, wo_category=1, mid_handler__in=[0, 1, 2])
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def set_lossing(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=8)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def recover(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=0)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if not obj.feedback:
                    data["error"].append("%s 无反馈内容, 不可以审核" % obj.track_id)
                    n -= 1
                    continue
                if obj.is_return:
                    if not obj.return_express_id:
                        data["error"].append("%s 返回的单据无返回单号" % obj.track_id)
                        n -= 1
                        continue
                if obj.is_losing:
                    if obj.process_tag != 8:
                        data["error"].append("%s 丢件必须确认丢失才可以审核" % obj.track_id)
                        n -= 1
                        continue
                obj.mid_handler = 3
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                if not obj.feedback:
                    data["error"].append("%s 无反馈内容" % obj.track_id)
                    n -= 1
                    continue
                else:
                    obj.order_status = 1
                    obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        data["false"] = len(reject_list) - n
        return Response(data)


class EWOSupplierHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        company = self.request.user.company
        queryset = ExpressWorkOrder.objects.filter(company=company, order_status=2, mid_handler=3).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        params["wo_category"] = 0
        params["company"] = user.company
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["wo_category"] = 0
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=2, mid_handler=3)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if not obj.feedback:
                    data["error"].append("%s 无反馈内容, 不可以审核" % obj.track_id)
                    n -= 1
                    continue
                if obj.is_return:
                    if not obj.return_express_id:
                        data["error"].append("%s 返回的单据无返回单号" % obj.track_id)
                        n -= 1
                        continue
                if obj.is_losing:
                    if obj.process_tag != 8:
                        data["error"].append("%s 丢件必须确认丢失才可以审核" % obj.track_id)
                        n -= 1
                        continue
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
                if not obj.feedback:
                    data["error"].append("%s 无反馈内容" % obj.track_id)
                    n -= 1
                    continue
                else:
                    obj.order_status = 1
                    obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        data["false"] = len(reject_list) - n
        return Response(data)


class EWOCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        queryset = ExpressWorkOrder.objects.filter(order_status=3).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=3)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:

                if order.is_losing:
                    order.order_status = 4
                else:
                    order.order_status = 5
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)


class EWOFinanceHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        queryset = ExpressWorkOrder.objects.filter(order_status=4).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)


class EWOManageViewset(viewsets.ModelViewSet):
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
    serializer_class = ExpressWorkOrderSerializer
    filter_class = ExpressWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = ExpressWorkOrder.objects.all().order_by("id")
        else:
            queryset = ExpressWorkOrder.objects.filter(company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
        return Response(data)
