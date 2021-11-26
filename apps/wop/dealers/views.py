import datetime, math
import re
import pandas as pd
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import DealerWorkOrder
from .serializers import DealerWorkOrderSerializer
from .filters import DealerWorkOrderFilter
from apps.base.company.models import Company



class DWOCreateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定经销商工单
    list:
        返回经销商工单列表
    update:
        更新销商工单
    destroy:
        删除销商工单
    create:
        创建销商工单
    partial_update:
        更新部分销商工单
    """
    serializer_class = DealerWorkOrderSerializer
    filter_class = DealerWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['dealers.view_user_dealerworkorder',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        user = self.request.user
        queryset = DealerWorkOrder.objects.filter(order_status=1, company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["company"] = user.company
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["company"] = user.company
        if all_select_tag:
            handle_list = DealerWorkOrderSerializer(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DealerWorkOrder.objects.filter(id__in=order_ids, order_status=1, company=user.company)
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
        error = data["error"].append
        if n:
            for obj in check_list:
                if obj.is_customer_post:
                    if not all([obj.return_express_id, obj.return_express_company]):
                        obj.mistake_tag = 1
                        obj.save()
                        n -= 1
                        error("%s 客户寄回，快递项必填" % obj.order_id)
                        continue
                obj.order_status = 2
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
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可取消的单据！")
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

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)
            columns_key_ori = df.columns.values.tolist()
            filter_fields = ["源订单单号", "单据类型", "初始问题信息", "货品", "数量", "金额","备注"]
            INIT_FIELDS_DIC = {
                "源订单单号": " order_id",
                "工单类型": "category",
                "初始问题信息": "information",
                "货品": "goods_name",
                "数量": "quantity",
                "金额": "amount",
                "备注": "memo"
            }
            result_keys = []
            for keywords in columns_key_ori:
                if keywords in filter_fields:
                    result_keys.append(keywords)

            try:
                df = df[result_keys]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            result_columns = []
            for keywords in columns_key:
                result_columns.append(INIT_FIELDS_DIC.get(keywords, None))

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = DealerWorkOrder.verify_mandatory(result_columns)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            ret_columns_key = dict(zip(columns_key, result_columns))
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
        error = report_dic["error"].append
        category_list = {
            '退货': 1,
            '换货': 2,
            '维修': 3,
        }
        user = request.user

        for row in resource:

            order_fields = ["order_id", "category", "information",  "goods_name", "quantity", "amount", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 公司错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = DealerWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.keyword = re.sub("[!$%&\'()*,./:;<=>?，。?★、…【】《》？“”‘’！[\\]^`{|}~\s]+", "", str(order.keyword).strip())

            try:
                order.creator = user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["track_id"])
                report_dic["false"] += 1

        return report_dic

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
        "GET": ['dealers.view_handler_dealerworkorder',]
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
                if not order.suggestion:
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
            for obj in reject_list:
                if not obj.rejection:
                    obj.mistake_tag =4
                    obj.save()
                    data["error"].append("%s 驳回原因为空" % obj.track_id)
                    n -= 1
                    continue
                obj.order_status = 1
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
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
        "GET": ['dealers.view_user_dealerworkorder',]
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
        if not user.is_our:
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
                if not order.feedback:
                    order.mistake_tag = 4
                    data["error"].append("%s 执行内容为空" % order.order_id)
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
                order.handle_interval = math.floor(total_seconds / 60)
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
            check_list.update(process_tag=1, feedback=confirm_content)
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
            for obj in reject_list:
                if not obj.rejection:
                    obj.mistake_tag = 4
                    obj.save()
                    data["error"].append("%s 驳回原因为空" % obj.track_id)
                    n -= 1
                    continue
                obj.order_status = 2
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
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
        "GET": ['dealers.view_check_dealerworkorder',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        queryset = DealerWorkOrder.objects.filter(order_status=4).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
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
                    order.mistake_tag = 5
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
            for obj in reject_list:
                if not obj.rejection:
                    obj.mistake_tag = 4
                    obj.save()
                    data["error"].append("%s 驳回原因为空" % obj.track_id)
                    n -= 1
                    continue
                obj.order_status = 2
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
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
        "GET": ['dealers.view_dealerworkorder',]
    }

    def get_queryset(self):
        if not self.request:
            return DealerWorkOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = DealerWorkOrder.objects.all().order_by("id")
        else:
            queryset = DealerWorkOrder.objects.filter(company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["company"] = user.company
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DealerWorkOrderFilter(params)
        serializer = DealerWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)













