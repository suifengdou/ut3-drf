import datetime, math
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
from .models import DealerWorkOrder
from .serializers import DealerWorkOrderSerializer
from .filters import DealerWorkOrderFilter



class DWOSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        user = self.request.user
        queryset = DealerWorkOrder.objects.filter(company=user.company, order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = DealerWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerWorkOrder.objects.filter(id__in=order_ids, company=self.request.user.company, order_status=1)
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
                if order.is_customer_post:
                    if not all([order.return_express_company, order.return_express_id]):
                        order.mistake_tag = 1
                        data["error"].append("%s 返回单号或快递为空" % order.order_id)
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


class DWOHandleViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        queryset = DealerWorkOrder.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = DealerWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerWorkOrder.objects.filter(id__in=order_ids, order_status=2)
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
                if not order.process_tag:
                    data["error"].append("%s 处理意见为空！" % order.order_id)
                    order.mistake_tag = 2
                    order.save()
                    n -= 1
                    continue
                if not order.is_losing:
                    if not all([order.return_express_company, order.return_express_id]):
                        data["error"].append("%s 返回快递和单号必填！" % order.order_id)
                        order.mistake_tag = 1
                        order.save()
                        n -= 1
                        continue
                order.submit_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(order.update_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(order.submit_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                order.services_interval = math.floor(total_seconds / 60)
                order.servicer = request.user.username
                order.order_status = 3
                order.mistake_tag = 0
                order.process_tag = 0
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DWOCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        user = self.request.user
        queryset = DealerWorkOrder.objects.filter(company=user.company, order_status=3).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 3
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["company"] = user.company
        params["order_status"] = 3
        if all_select_tag:
            handle_list = DealerWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerWorkOrder.objects.filter(id__in=order_ids, company=user.company, order_status=3)
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
                if not order.process_tag:
                    order.mistake_tag = 4
                    data["error"].append("%s 先标记为已处理才能审核" % order.order_id)
                    order.save()
                    n -= 1
                    continue
                order.handle_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(order.submit_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(order.handle_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                order.express_interval = math.floor(total_seconds / 60)
                order.handler = request.user.username
                order.order_status = 4
                order.mistake_tag = 0
                order.process_tag = 0
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_confirm(self, request, *args, **kwargs):
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
            confirm_content = "已确认{%s-%s}" % (self.request.user.username, datetime.date.today())
            check_list.update(process_tag=1, memo=confirm_content)
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


class DWOConfirmViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        queryset = DealerWorkOrder.objects.filter(order_status=4).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 4
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 4
        if all_select_tag:
            handle_list = DealerWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerWorkOrder.objects.filter(id__in=order_ids, order_status=4)
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
                if not order.process_tag:
                    order.mistake_tag = 4
                    data["error"].append("%s 先标记为已处理才能审核" % order.order_id)
                    order.save()
                    n -= 1
                    continue
                order.order_status = 5
                order.mistake_tag = 0
                order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


    @action(methods=['patch'], detail=False)
    def set_confirm(self, request, *args, **kwargs):
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
            check_list.update(process_tag=1)
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
            reject_list.update(order_status=3)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class DWOManageViewset(viewsets.ModelViewSet):
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
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = DealerWorkOrder.objects.all().order_by("id")
        else:
            queryset = DealerWorkOrder.objects.filter(company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.category:
            request.data["company"] = user.company
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)













