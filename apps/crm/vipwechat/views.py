import datetime, math
import pandas as pd
import re
from decimal import Decimal
import numpy as np
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import Specialist, VIPWechat
from .serializers import SpecialistSerializer, VIPWechatSerializer
from .filters import SpecialistFilter, VIPWechatFilter
from ut3.settings import EXPORT_TOPLIMIT
from apps.crm.customers.models import Customer



class SpecialistViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定专属客服
    list:
        返回专属客服
    update:
        更新专属客服
    destroy:
        删除专属客服
    create:
        创建专属客服
    partial_update:
        更新部分专属客服
    """
    serializer_class = SpecialistSerializer
    filter_class = SpecialistFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['vipwechat.view_specialist']
    }

    def get_queryset(self):
        if not self.request:
            return Specialist.objects.none()
        queryset = Specialist.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = SpecialistFilter(params)
        serializer = SpecialistSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = self.request.user.company
        if all_select_tag:
            handle_list = SpecialistFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Specialist.objects.filter(id__in=order_ids, order_status=1)
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


class VIPWechatMyselfViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定客户列表明细
    list:
        返回客户列表
    update:
        更新客户列表
    destroy:
        删除客户列表
    create:
        创建客户列表
    partial_update:
        更新部分客户列表
    """
    serializer_class = VIPWechatSerializer
    filter_class = VIPWechatFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['vipwechat.view_vipwechat']
    }

    def get_queryset(self):
        if not self.request:
            return VIPWechat.objects.none()
        user = self.request.user

        queryset = VIPWechat.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = VIPWechatFilter(params)
        serializer = VIPWechatSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = self.request.user.username
        if all_select_tag:
            handle_list = VIPWechatFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = VIPWechat.objects.filter(id__in=order_ids, order_status=1)
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
                order.order_status = 2
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

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):

        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            "客户": "customer",
            "服务账号": "specialist",
            "客户微信": "cs_wechat",
            "备注": "memo",
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["客户", "服务账号", "客户微信", "备注"]

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = VIPWechat.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)

            # 更改一下DataFrame的表名称
            num_end = 0
            step = 300
            step_num = int(len(df) / step) + 2
            i = 1
            while i < step_num:
                num_start = num_end
                num_end = step * i
                intermediate_df = df.iloc[num_start: num_end]

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                _ret_list = intermediate_df.to_dict(orient='records')
                intermediate_report_dic = self.save_resources(request, _ret_list)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:

            _q_customer = Customer.objects.filter(name=row["customer"])
            if _q_customer.exists():
                customer = _q_customer[0]
            else:
                customer = Customer()
                customer.name = row["customer"]
                customer.save()

            _q_specialist = Specialist.objects.filter(smartphone=row["specialist"])
            if _q_specialist.exists():
                specialist = _q_specialist[0]
            else:
                report_dic["false"] += 1
                report_dic["error"].append("%s 错误的服务账号！" % row["specialist"])
                continue

            if not re.match(r"^[0-9]+$", row["cs_wechat"]):
                report_dic["false"] += 1
                report_dic["error"].append("%s 错误的客户微信号！" % row["cs_wechat"])
                continue
            row["memo"] = row["memo"][:249]

            _q_vipwechat = VIPWechat.objects.filter(customer=customer)
            if _q_vipwechat.exists():
                report_dic["false"] += 1
                report_dic["error"].append("%s 已存在此客户！" % row["customer"])
                continue
            else:
                order = VIPWechat()
            order.customer = customer
            order.specialist = specialist
            order.cs_wechat = row["cs_wechat"]
            order.memo = row["memo"]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["goods_id"])
                report_dic["false"] += 1
        return report_dic


class VIPWechatManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定客户列表
    list:
        返回客户列表
    update:
        更新客户列表
    destroy:
        删除客户列表
    create:
        创建客户列表
    partial_update:
        更新部分客户列表
    """
    serializer_class = VIPWechatSerializer
    filter_class = VIPWechatFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['vipwechat.view_vipwechat']
    }

    def get_queryset(self):
        if not self.request:
            return VIPWechat.objects.none()
        queryset = VIPWechat.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = VIPWechatFilter(params)
        serializer = VIPWechatSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = VIPWechatFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = VIPWechat.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list



