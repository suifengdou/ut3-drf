import re, datetime, math
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
from .models import StorageWorkOrder
from .serializers import StorageWorkOrderSerializer
from .filters import StorageWorkOrderFilter


class SWOReverseCreateViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        user = self.request.user
        queryset = StorageWorkOrder.objects.filter(company=user.company, order_status=1,  wo_category=1).order_by("id")
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
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(order_status=2, is_return=0)
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


class SWOCreateViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        user = self.request.user
        queryset = StorageWorkOrder.objects.filter(company=user.company, order_status=1, wo_category=0).order_by("id")
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
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["wo_category"] = 0
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=1, wo_category=0)
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
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for order in check_list:
                order.servicer = request.user.username
                order.submit_time = datetime.datetime.now()
                order.order_status = 2
                order.is_return = 1
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


class SWOHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        user = self.request.user
        queryset = StorageWorkOrder.objects.filter(order_status=2, is_return=0, wo_category=1).order_by("id")
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
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["wo_category"] = 1
        params["is_return"] = 0
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=2, is_return=0, wo_category=1)
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
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if not obj.feedback:
                    data["error"].append("%s 无反馈内容, 不可以审核" % obj.track_id)
                    n -= 1
                    continue

                obj.submit_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(obj.create_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(obj.submit_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                obj.services_interval = math.floor(total_seconds / 60)
                obj.servicer = request.user.username
                obj.is_return = 1
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class SWOSupplierHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        user = self.request.user
        queryset = StorageWorkOrder.objects.filter(company=user.company, order_status=2, is_return=1).order_by("id")
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
        params["is_return"] = 1
        params["company"] = user.company
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["wo_category"] = 0
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=2, is_return=1)
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
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.wo_category:
                    if not obj.memo:
                        data["error"].append("%s 逆向结单备注不能为空" % obj.track_id)
                        n -= 1
                        continue
                else:
                    if not obj.feedback:
                        data["error"].append("%s 正常工单反馈不能为空" % obj.track_id)
                        n -= 1
                        continue


                obj.handle_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(obj.submit_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(obj.handle_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                obj.express_interval = math.floor(total_seconds / 60)
                obj.handler = request.user.username
                obj.order_status = 3
                obj.mistake_tag = 0
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
            for obj in reject_list:
                if obj.wo_category == 0:
                    obj.order_status = 1
                else:
                    obj.is_return = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)


class SWOCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        queryset = StorageWorkOrder.objects.filter(order_status=3).order_by("id")
        return queryset


    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=3)
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
            "successful": 0,
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
            reject_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class SWOFinanceHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        queryset = StorageWorkOrder.objects.filter(order_status=4).order_by("id")
        return queryset


    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 4
        if all_select_tag:
            handle_list = StorageWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = StorageWorkOrder.objects.filter(id__in=order_ids, order_status=4)
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
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(order_status=5)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)


class SWOManageViewset(viewsets.ModelViewSet):
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
    serializer_class = StorageWorkOrderSerializer
    filter_class = StorageWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return StorageWorkOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = StorageWorkOrder.objects.all().order_by("id")
        else:
            queryset = StorageWorkOrder.objects.filter(company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["company"] = user.company
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = StorageWorkOrderFilter(params)
        serializer = StorageWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)




