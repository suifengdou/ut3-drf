import re, datetime
import math
import pandas as pd
import numpy as np
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from django.http.response import HttpResponse, JsonResponse
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import LogisticsSerializer, DepponSerializer
from .filters import LogisticsFilter, DepponFilter
from .models import Logistics, Deppon, LogDeppon, LogLogistics
from apps.auth.users.models import UserProfile
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.utils.logging.loggings import logging, getlogs
from apps.sales.trialgoods.models import RefundTrialOrder
import time
import hashlib
import base64
import requests
import json
from ut3.settings import DEPPON_API


class LogisticsViewset(viewsets.ModelViewSet):
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
    serializer_class = LogisticsSerializer
    filter_class = LogisticsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['logistics.view_logistics']
    }

    def get_queryset(self):
        if not self.request:
            return Logistics.objects.none()
        user = self.request.user
        queryset = Logistics.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = LogisticsFilter(params)
        serializer = LogisticsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = LogisticsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Logistics.objects.filter(id__in=order_ids, order_status=1)
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
                _q_repeated_order = Logistics.objects.filter(sent_consignee=obj.sent_consignee,
                                                                order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
                        obj.save()
                        n -= 1
                        continue
                _q_repeated_order = Logistics.objects.filter(sent_smartphone=obj.sent_smartphone,
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


class DepponReceptionViewset(viewsets.ModelViewSet):
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
    serializer_class = DepponSerializer
    filter_class = DepponFilter
    filter_fields = "__all__"
    permission_classes = (AllowAny, )

    def get_queryset(self):
        return Deppon.objects.none()

    @action(methods=['post'], detail=False)
    def information(self, request, *args, **kwargs):
        status_signs = {
            "FAILGOT": 1,
            "SIGNSUCCESS": 2,
            "GOT": 3,
            "ACCEPT": 4,
            "SIGNFAILED": 5,
            "RECEIPTING": 6,
            "CANCEL": 7,
            "GOBACK": 8,
        }
        status_description = {
            "FAILGOT": "揽货失败",
            "SIGNSUCCESS": "正常签收",
            "GOT": "开单",
            "ACCEPT": "已受理",
            "SIGNFAILED": "异常签收",
            "RECEIPTING": "接货中",
            "CANCEL": "已撤销",
            "GOBACK": "已退回",
        }
        res_data = {
            "logisticCompanyID": "DEPPON",
            "logisticID": "",
            "result": "true",
            "resultCode": "1000",
            "reason": "成功"
        }
        params = json.loads(request.data["params"])
        res_data["logisticID"] = params["logisticID"]
        _q_express_order = Deppon.objects.filter(logisticID=params["logisticID"])
        if _q_express_order.exists():
            express_order = _q_express_order[0]
        else:
            res_data["reason"] = "系统未找到单据"
        if express_order.order_status in [1, 2, 7, 8]:
            res_data["reason"] = "单据状态已锁定"
        order_status = status_signs.get(params["statusType"], 0)
        if order_status:
            express_order.order_status = order_status
            express_order.save()
            _q_refund_order = RefundTrialOrder.objects.filter(code=express_order.order.code)
            if _q_refund_order.exists():
                refund_order = _q_refund_order[0]
                if express_order.order_status == 1:
                    refund_order.info_refund = "德邦揽件失败，如果还需取件，需要撤销快递，然后更新单号重新获取单号。"
                elif express_order.order_status in [7, 8]:
                    refund_order.info_refund = "快递已被撤销，或者已经退回发件方，需要核实具体情况。"
                else:
                    refund_order.info_refund = status_description.get(params["statusType"], None)
                refund_order.save()
                res_data["reason"] = "回传成功"
            else:
                res_data["reason"] = "回传成功"
        else:
            res_data["result"] = "false"
            res_data["resultCode"] = "500"
            res_data["reason"] = "单据状态信息无法识别"
            express_order.reason = f"错误的状态码：{params['statusType']}"
            express_order.save()
        # res_data = json.dumps(res_data)

        current_time = time.time()
        time_stamp = str(int(round(current_time * 1000)))
        app_key = express_order.order.express.app_key
        plainText = f"{res_data}{app_key}{time_stamp}"
        digest = hashlib.md5(plainText.encode("utf-8")).hexdigest()
        digest = str(base64.b64encode(digest.encode("utf-8")), encoding='utf-8')
        return HttpResponse(content=json.dumps({
            "params": res_data,
            "digest": digest,
            "timestamp": time_stamp,
            "companyCode": express_order.order.express.auth_name,
        }), content_type="application/json", status=200)


class DepponViewset(viewsets.ModelViewSet):
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
    serializer_class = DepponSerializer
    filter_class = DepponFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
         "GET": ['logistics.view_logistics']
    }

    def get_queryset(self):
        if not self.request:
            return Deppon.objects.none()
        user = self.request.user
        queryset = Deppon.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = DepponFilter(params)
        serializer = DepponSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = DepponFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Deppon.objects.filter(id__in=order_ids, order_status=1)
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
                _q_repeated_order = Logistics.objects.filter(sent_consignee=obj.sent_consignee,
                                                                order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
                        obj.save()
                        n -= 1
                        continue
                _q_repeated_order = Logistics.objects.filter(sent_smartphone=obj.sent_smartphone,
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


def get_model_logistic(express):
    customer_label_dict = {
        "DEPPON": Deppon,
    }
    model_class = customer_label_dict.get(express.category.code, -1)
    return {"model": model_class}


def get_create_logistic(express):
    customer_label_dict = {
        "DEPPON": CreateDepponOrder,
    }
    create_function = customer_label_dict.get(express.category.code, -1)
    return {"function": create_function}


def check_fields(data):
    VERIFY_FIELD = ["code", "warehouse", "express", "sender", "receiver", "weight", "goods_name"]
    check_list = data.keys()
    for i in VERIFY_FIELD:
        if i not in check_list:
            return {"false": 1, "error": [f"缺失字段{i}"]}
    else:
        return None


# 创建物流单
def CreateLogisticOrder(request, data=None, *args, **kwargs):
    user = request.user
    reback_data = dict({
        "successful": 0,
        "false": 0,
        "error": []
    })
    if not data:
        reback_data["false"] = 1
        reback_data["error"].append("未传输数据")
        return reback_data
    else:
        check_data = check_fields(data)
        if check_data:
            return check_data
    try:
        _q_logistics_order = Logistics.objects.filter(code=data["code"])
        if _q_logistics_order.exists():
            logistics_order = _q_logistics_order[0]
            if logistics_order.order_status in [0, 1]:
                logistics_order.order_status = 1
                logistics_order.save()
            else:
                reback_data["false"] = 1
                reback_data["error"].append("已存在处理完成的物流单")
                return reback_data
        else:
            logistics_order_dict = {
                "code": data["code"],
                "warehouse": data["warehouse"],
                "express": data["express"],
                "creator": user.username
            }
            logistics_order = Logistics.objects.create(**logistics_order_dict)
            logging(logistics_order, user, LogLogistics, "创建物流单")
    except Exception as e:
        reback_data["false"] = 1
        reback_data["error"].append(f"物流单创建失败：{e}")
        return reback_data

    express_type = get_model_logistic(data["express"])
    if express_type["model"] == -1:
        reback_data["false"] = 1
        reback_data["error"].append("不支持此物流")
        return reback_data

    express_func = get_create_logistic(data["express"])
    if express_func["function"] == -1:
        reback_data["false"] = 1
        reback_data["error"].append("不支持此物流对接")
        return reback_data

    express_order = express_func["function"](request, logistics_order, data)

    if not express_order:
        reback_data["false"] = 1
        reback_data["error"].append("创建快递明细单出错")
        return reback_data
    else:
        reback_data["successful"] = 1
        return reback_data


# 创建德邦快递详情单
def CreateDepponOrder(request, logistics_order, data=None, *args, **kwargs):
    user = request.user
    if data["weight"] <= 3000:
        transportType = "PACKAGE"
    else:
        transportType = "RCP"
    deppon_order_dict = {
        "order": logistics_order,
        "logisticID": f"{logistics_order.express.sign}{logistics_order.code}",
        "custOrderNo": f"{logistics_order.code}",
        "companyCode": f"{logistics_order.express.auth_name}",
        "transportType": transportType,
        "customerCode": f"{logistics_order.express.auth_code}",
        "orderType": 1,
        "sender": data["sender"],
        "receiver": data["receiver"],
        "cargoName": str(data["goods_name"])[:239],
        "totalNumber": 1,
        "totalWeight": round(data["weight"] / 1000, 2),
        "deliveryType": 2,
        "payType": 3,
        "smsNotify": "Y",
        "creator": user.username,
    }
    try:
        deppon_order = Deppon.objects.create(**deppon_order_dict)
        logging(deppon_order, user, LogDeppon, "创建")
    except Exception as e:
        return Deppon.objects.none()
    return deppon_order


