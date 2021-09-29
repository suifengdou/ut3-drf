import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np

import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict
from django.db.models import Count, Max, Min, Avg
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
from .models import Compensation, BatchCompensation, BCDetail, BCDetailResetList
from .serializers import CompensationSerializer, BatchCompensationSerializer, BCDetailSerializer
from .filters import CompensationFilter, BatchCompensationFilter, BCDetailFilter
from apps.utils.geography.models import City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from ut3.settings import EXPORT_TOPLIMIT


class CompensationSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = CompensationSerializer
    filter_class = CompensationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_compensation']
    }

    def get_queryset(self):
        if not self.request:
            return Compensation.objects.none()
        queryset = Compensation.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = CompensationFilter(params)
        serializer = CompensationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = CompensationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Compensation.objects.filter(id__in=order_ids, order_status=1)
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
        check_category = list(check_list.values("shop", "order_category").annotate(Count("id")))
        if len(check_category) > 1:
            raise serializers.ValidationError("只能选择单一店铺单一类型！")
        shop = check_list[0].shop
        order_category = check_list[0].order_category
        _q_batch_order = BatchCompensation.objects.filter(order_status=1, shop=shop, order_category=order_category)
        if _q_batch_order.exists():
            order = _q_batch_order[0]
        else:
            order = BatchCompensation()
            order.shop = shop
            order.order_category = order_category
            serial_number = str(datetime.date.today()).replace("-", "")
            try:
                index = BatchCompensation.objects.last()
                index_num = int(index.id) + 1
            except:
                index_num = 1
            order.order_id = str(serial_number) + "BO" + str(index_num)
            try:
                order.creator = request.user.username
                order.save()
            except Exception as e:
                raise serializers.ValidationError("创建汇总单失败！")
        if n:
            for obj in check_list:
                _q_repeat_order = Compensation.objects.filter(order_id=obj.order_id, order_status__in=[1, 2])
                if len(_q_repeat_order) > 1:
                    if obj.process_tag != 2:
                        data["error"].append("%s 建单重复" % obj.id)
                        n -= 1
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                if not obj.erp_order_id:
                    _prefix = "MO"
                    serial_number = str(datetime.date.today()).replace("-", "")
                    obj.erp_order_id = serial_number + _prefix + str(obj.id)
                    obj.save()
                try:
                    detail_order = obj.bcdetail
                    if detail_order.order_status in [0, 1]:
                        detail_order.order_status = 1
                    else:
                        data["error"].append("%s 递交重复" % obj.id)
                        n -= 1
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                except:
                    detail_order = BCDetail()
                    detail_order.compensation_order = obj
                detail_order.batch_order = order
                detail_order_fields = ["servicer", "goods_name", "nickname", "order_id", "compensation",
                                       "name", "alipay_id", "actual_receipts", "receivable",
                                       "checking", "memorandum", "erp_order_id"]
                for key_word in detail_order_fields:
                    setattr(detail_order, key_word, getattr(obj, key_word, None))
                try:
                    detail_order.creator = request.user.username
                    detail_order.save()
                except Exception as e:
                    data["error"].append("%s 保存批次单明细失败" % obj.id)
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.handler = request.user.username
                obj.handle_time = datetime.datetime.now()
                if obj.process_tag != 2:
                    obj.process_tag = 1
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
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=2)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reset_tag(self, request, *args, **kwargs):
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            set_list.update(process_tag=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class CompensationViewset(viewsets.ModelViewSet):
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
    serializer_class = CompensationSerializer
    filter_class = CompensationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_compensation',]
    }

    def get_queryset(self):
        if not self.request:
            return Compensation.objects.none()
        queryset = Compensation.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = CompensationFilter(params)
        serializer = CompensationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


class BatchCompensationSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = BatchCompensationSerializer
    filter_class = BatchCompensationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_user_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BatchCompensation.objects.none()
        queryset = BatchCompensation.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = BatchCompensationFilter(params)
        serializer = BatchCompensationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = BatchCompensationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BatchCompensation.objects.filter(id__in=order_ids, order_status=1)
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
                if not obj.oa_order_id:
                    data["error"].append("%s 无OA单号" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                obj.bcdetail_set.all().update(order_status=2)
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
            for obj in reject_list:
                details = obj.bcdetail_set.all()
                for detail in details:
                    detail.compensation_order.order_status = 1
                    detail.compensation_order.save()
                details.delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class BatchCompensationSettleViewset(viewsets.ModelViewSet):
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
    serializer_class = BatchCompensationSerializer
    filter_class = BatchCompensationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_handler_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BatchCompensation.objects.none()
        queryset = BatchCompensation.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = BatchCompensationFilter(params)
        serializer = BatchCompensationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = BatchCompensationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BatchCompensation.objects.filter(id__in=order_ids, order_status=2)
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
                _q_successful = obj.bcdetail_set.filter(order_status=2)
                if not _q_successful.exists():
                    obj.mistake_tag = 0
                    obj.order_status = 3
                    obj.save()
                else:
                    n -= 1
                    data["error"].append("%s 有未完成的明细" % obj.id)
                    obj.mistake_tag = 2
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class BatchCompensationViewset(viewsets.ModelViewSet):
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
    serializer_class = BatchCompensationSerializer
    filter_class = BatchCompensationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BatchCompensation.objects.none()
        queryset = BatchCompensation.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = BatchCompensationFilter(params)
        serializer = BatchCompensationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


class BCDetailSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = BCDetailSerializer
    filter_class = BCDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_user_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BCDetail.objects.none()
        queryset = BCDetail.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["company"] = user.company
        params["order_status"] = 1
        f = BCDetailFilter(params)
        serializer = BCDetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = BCDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BCDetail.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

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
                compensation_order = obj.compensation_order
                compensation_order.order_status = 1
                compensation_order.save()
                batch_order = obj.batch_order
                obj.delete()
                all_details = batch_order.bcdetail_set.all()
                if len(all_details) == 0:
                    batch_order.order_status = 0
                    batch_order.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class BCDetailSettleViewset(viewsets.ModelViewSet):
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
    serializer_class = BCDetailSerializer
    filter_class = BCDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_handler_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BCDetail.objects.none()
        queryset = BCDetail.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = BCDetailFilter(params)
        serializer = BCDetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = BCDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = BCDetail.objects.filter(id__in=order_ids, order_status=2)
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
                if obj.paid_amount != obj.compensation:
                    data["error"].append("%s 补运费和已付不相等" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if not obj.is_payment:
                    data["error"].append("%s 未支付状态" % obj.id)
                    n -= 1
                    obj.mistake_tag = 2
                    obj.save()
                    continue
                if obj.process_tag != 0:
                    data["error"].append("%s 处理标签错误" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                obj.handler = request.user.username
                obj.handle_time = datetime.datetime.now()
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
                batch_order = obj.batch_order
                _q_successful = batch_order.bcdetail_set.filter(order_status=2)
                if not _q_successful.exists():
                    batch_order.order_status = 3
                    batch_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


    @action(methods=['patch'], detail=False)
    def reset(self, request, *args, **kwargs):
        user = request.user.username
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        mistake_dic = {
            1: "无效支付宝",
            2: "支付宝和收款人不匹配"
        }
        if n:
            for obj in check_list:
                try:
                    reset_list_order = obj.bcdetailresetlist
                    data["error"].append("%s 已重置不可重复" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                except:
                    pass
                if obj.paid_amount != 0:
                    data["error"].append("%s 已付金额不是零，不可重置" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                if obj.process_tag == 0:
                    data["error"].append("%s 处理标签错误" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue

                order = Compensation()
                detail_fields = ["servicer", "goods_name", "nickname", "order_id", "compensation", "name", "alipay_id",
                                 "actual_receipts", "receivable", "checking", "memorandum"]
                for key_word in detail_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))
                reset_reason = mistake_dic.get(order.process_tag, None)
                order.memorandum = "%s #财务中心%s 重置补偿单，重置原因是 %s" % (order.memorandum, user, reset_reason)
                order.shop = obj.batch_order.shop
                order.order_category = obj.batch_order.order_category
                reset_list_order = BCDetailResetList()
                reset_list_order.bcdetail = obj
                try:
                    order.creator = request.user.username
                    order.save()
                    reset_list_order.save()
                except Exception as e:
                    data["error"].append("%s 单据创建失败" % str(obj.id))
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
                batch_order = obj.batch_order
                _q_successful = batch_order.bcdetail_set.filter(order_status=2)
                if not _q_successful.exists():
                    batch_order.order_status = 3
                    batch_order.save()
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
                obj.mogoods_set.all().delete()
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class BCDetailViewset(viewsets.ModelViewSet):
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
    serializer_class = BCDetailSerializer
    filter_class = BCDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['compensation.view_batchcompensation']
    }

    def get_queryset(self):
        if not self.request:
            return BCDetail.objects.none()
        queryset = BCDetail.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = BCDetailFilter(params)
        serializer = BCDetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)











