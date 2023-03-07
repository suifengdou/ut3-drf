import re, math
import datetime
import pandas as pd
from itertools import islice
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
import oss2
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import JobCategory, JobOrder, JOFiles, JobOrderDetails, LogJobCategory, LogJobOrder, \
    LogJobOrderDetails, JODFiles
from .serializers import JobCategorySerializer, JobOrderSerializer, JobOrderDetailsSerializer, JOFilesSerializer, JODFilesSerializer
from .filters import JobCategoryFilter, JobOrderFilter, JobOrderDetailsFilter, JOFilesFilter, JODFilesFilter
from ut3.settings import EXPORT_TOPLIMIT
from apps.base.company.models import Company
from apps.crm.customers.models import Customer, LogCustomer

from ut3.settings import OSS_CONFIG, EXPORT_TOPLIMIT

from apps.utils.oss.aliyunoss import AliyunOSS
from apps.utils.logging.loggings import getlogs, logging, getfiles


class JobCategoryViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务类型
    list:
        返回任务类型
    """
    serializer_class = JobCategorySerializer
    filter_class = JobCategoryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['order.view_OriOrder']
    }

    def get_queryset(self):
        if not self.request:
            return JobCategory.objects.none()
        queryset = JobCategory.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = JobCategoryFilter(params)
        serializer = JobCategorySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = JobCategory.objects.filter(id=id)[0]
        ret = getlogs(instance, LogJobCategory)
        return Response(ret)


class JobOrderSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务工单
    list:
        返回任务工单
    update:
        更新任务工单
    destroy:
        删除任务工单
    create:
        创建任务工单
    partial_update:
        更新部分任务工单
    """
    serializer_class = JobOrderSerializer
    filter_class = JobOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        user = self.request.user
        if not self.request:
            return JobOrder.objects.none()
        queryset = JobOrder.objects.filter(order_status=1, department=user.department).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["department"] = user.department
        f = JobOrderFilter(params)
        serializer = JobOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["department"] = user.department
        if all_select_tag:
            handle_list = JobOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        user = request.user
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
                if obj.process_tag != 1:
                    obj.mistake_tag = 1
                    obj.save()
                    logging(obj, user, LogJobOrder, "审核失败：任务明细未完整确认")
                    data["error"].append("%s 任务明细未完整确认，不可审核" % obj.code)
                    n -= 1
                    continue

                all_details = obj.joborderdetails_set.filter(order_status=1)
                _q_check_details = all_details.filter(process_tag=0)
                if _q_check_details.exists():
                    obj.mistake_tag = 2
                    obj.process_tag = 0
                    obj.save()
                    logging(obj, user, LogJobOrder, "审核失败：存在未锁定单据明细")
                    data["error"].append("%s 存在未锁定单据明细，锁定后再审核" % obj.code)
                    n -= 1
                    continue
                obj.quantity = all_details.count()
                for detail in all_details:
                    detail.order_status = 2
                    detail.process_tag = 0
                    detail.checker = user.username
                    detail.checked_time = datetime.datetime.now()
                    detail.save()
                    logging(detail, user, LogJobOrderDetails, "审核")
                obj.order_status = 2
                obj.process_tag = 0
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogJobOrder, "审核")
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
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborder"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JOFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrder, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderTrackViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务工单
    list:
        返回任务工单
    update:
        更新任务工单
    destroy:
        删除任务工单
    create:
        创建任务工单
    partial_update:
        更新部分任务工单
    """
    serializer_class = JobOrderSerializer
    filter_class = JobOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        user = self.request.user
        if not self.request:
            return JobOrder.objects.none()
        queryset = JobOrder.objects.filter(order_status=2, department=user.department).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        params["department"] = user.department
        f = JobOrderFilter(params)
        serializer = JobOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["department"] = user.department
        if all_select_tag:
            handle_list = JobOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrder.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        user = request.user
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
                pass
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        user = request.user
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
                all_details = obj.joborderdetails_set.all()
                _q_reject_details = all_details.filter(process_tag=0, order_status=2)
                _q_reject_quantity = _q_reject_details.count()
                if _q_reject_quantity != obj.quantity:
                    obj.mistake_tag = 3
                    obj.save()
                    logging(obj, user, LogJobOrder, "驳回失败：任务明细非初始状态")
                    data["error"].append("%s 任务明细非初始状态，不可驳回" % obj.code)
                    n -= 1
                    continue
                for detail in _q_reject_details:
                    detail.order_status = 1
                    detail.save()
                    logging(detail, user, LogJobOrderDetails, "驳回成功")
                obj.order_status = 1
                obj.save()
                logging(obj, user, LogJobOrder, "驳回成功")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborder"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JOFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrder, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务工单
    list:
        返回任务工单
    update:
        更新任务工单
    destroy:
        删除任务工单
    create:
        创建任务工单
    partial_update:
        更新部分任务工单
    """
    serializer_class = JobOrderSerializer
    filter_class = JobOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        user = self.request.user
        is_forward = bool(1 - user.is_our)
        if not self.request:
            return JobOrder.objects.none()
        queryset = JobOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        if not user.is_our:
            params["company"] = user.company
        f = JobOrderFilter(params)
        serializer = JobOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = JobOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogJobOrder)
        return Response(ret)

    @action(methods=['patch'], detail=False)
    def get_file_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = JobOrder.objects.filter(id=id)[0]
        ret = getfiles(instance, JOFiles)
        return Response(ret)


class JOFilesViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务工单文档
    list:
        返回任务工单文档
    update:
        更新任务工单文档
    destroy:
        删除任务工单文档
    create:
        创建任务工单文档
    partial_update:
        更新部分任务工单文档
    """
    serializer_class = JOFilesSerializer
    filter_class = JOFilesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return JOFiles.objects.none()
        queryset = JOFiles.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def delete_file(self, request):
        id = request.data.get("id", None)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if id:
            files_order = JOFiles.objects.filter(id=id, creator=user, is_delete=False)
            if files_order.exists():
                file_order = files_order[0]
                file_order.is_delete = 1
                file_order.save()
                data["successful"] += 1
                logging(file_order.workorder, user, LogJobOrder, "删除文档：%s" % file_order.name)
            else:
                data["false"] += 1
                data["error"].append("只有创建者才有删除权限")
        else:
            data["false"] += 1
            data["error"].append("没有找到删除对象")
        return Response(data)


class JobOrderDetailsSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细
    list:
        返回任务明细
    update:
        更新任务明细
    destroy:
        删除任务明细
    create:
        创建任务明细
    partial_update:
        更新部分任务明细
    """
    serializer_class = JobOrderDetailsSerializer
    filter_class = JobOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return JobOrderDetails.objects.none()
        user = self.request.user
        queryset = JobOrderDetails.objects.filter(order__department=user.department, order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = JobOrderDetailsFilter(params)
        serializer = JobOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = JobOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrderDetails.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        user = request.user
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
                obj.process_tag = 1
                obj.save()
                logging(obj, user, LogJobOrderDetails, "锁定")
                _q_order_complete = obj.order.joborderdetails_set.filter(process_tag=0, order_status=1)
                if not _q_order_complete.exists():
                    obj.order.process_tag = 1
                    obj.order.save()
                    logging(obj.order, user, LogJobOrder, "完成明细锁定")
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
        user = request.user
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            '手机': 'customer',
            '任务编码': 'code',
            '备注': 'memo',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["手机", "任务编码", '备注']

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                raise serializers.ValidationError("必要字段不全或者错误: %s" % e)

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = JobOrderDetails.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            columns_key_ori = df.columns.values.tolist()
            ret_columns_key = dict(zip(columns_key_ori, columns_key))
            df.rename(columns=ret_columns_key, inplace=True)
            code_dict = {}
            codes = list(set(df.code))
            for code in codes:
                _q_order = JobOrder.objects.filter(code=code, order_status=1)
                if _q_order.exists():
                    code_dict[code] = _q_order[0]

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
                intermediate_report_dic = self.save_resources(request, _ret_list, code_dict)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            for code in codes:
                code_dict[code].quantity = code_dict[code].joborderdetails_set.filter(order_status=1).count()
                code_dict[code].save()
                logging(code_dict[code], user, LogJobOrder, "更新数量：%s" % code_dict[code].quantity)
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource, code_dict):
        # 设置初始报告

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        for row in resource:
            user = request.user
            order_details = JobOrderDetails()
            order = code_dict.get(row["code"], None)
            if not order:
                report_dic["error"].append("%s 不存在待处理关联单" % row["code"])
                report_dic["false"] += 1
                continue
            order_details.order = order
            row["customer"] = re.sub("[!$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(row["customer"]))
            if not re.match(r"^1[23456789]\d{9}$", row["customer"]):
                report_dic["error"].append("%s 电话不符合规则" % row["customer"])
                report_dic["false"] += 1
                continue
            _q_customer = Customer.objects.filter(name=row["customer"])
            if _q_customer.exists():
                customer = _q_customer[0]
                _q_repeated_details = JobOrderDetails.objects.filter(order=order, customer=customer)
                if _q_repeated_details.exists():
                    report_dic["error"].append("%s 同一关联单电话重复" % row["customer"])
                    report_dic["false"] += 1
                    continue
                order_details.customer = customer
            else:

                customer = Customer.objects.create(**{"name": row["customer"]})
                logging(customer, user, LogCustomer, "源自任务创建")
                order_details.customer = customer
            order_details.memo = row['memo']
            try:
                order_details.creator = user.username
                order_details.save()
                logging(order_details, user, LogJobOrderDetails, "创建")
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
        return report_dic

    @action(methods=['patch'], detail=False)
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrderDetails.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborderdetails"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JODFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrderDetails, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderDetailsAcceptViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细
    list:
        返回任务明细
    update:
        更新任务明细
    destroy:
        删除任务明细
    create:
        创建任务明细
    partial_update:
        更新部分任务明细
    """
    serializer_class = JobOrderDetailsSerializer
    filter_class = JobOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return JobOrderDetails.objects.none()
        user = self.request.user
        queryset = JobOrderDetails.objects.filter(order__department=user.department, order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = JobOrderDetailsFilter(params)
        serializer = JobOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = JobOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrderDetails.objects.filter(id__in=order_ids, order_status=1)
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
                if not re.match(r'^[SFYT0-9]+$', obj.track_id):
                    obj.mistake_tag = 1
                    obj.save()
                    data["error"].append("%s 快递单号错误" % obj.track_id)
                    n -= 1
                    continue

                obj.order_status = 2
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
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrderDetails.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborderdetails"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JODFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrderDetails, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderDetailsPerformViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细
    list:
        返回任务明细
    update:
        更新任务明细
    destroy:
        删除任务明细
    create:
        创建任务明细
    partial_update:
        更新部分任务明细
    """
    serializer_class = JobOrderDetailsSerializer
    filter_class = JobOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return JobOrderDetails.objects.none()
        user = self.request.user
        queryset = JobOrderDetails.objects.filter(order__department=user.department, order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = JobOrderDetailsFilter(params)
        serializer = JobOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = JobOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrderDetails.objects.filter(id__in=order_ids, order_status=1)
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
                if not re.match(r'^[SFYT0-9]+$', obj.track_id):
                    obj.mistake_tag = 1
                    obj.save()
                    data["error"].append("%s 快递单号错误" % obj.track_id)
                    n -= 1
                    continue

                obj.order_status = 2
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
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrderDetails.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborderdetails"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JODFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrderDetails, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderDetailsTrackViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细
    list:
        返回任务明细
    update:
        更新任务明细
    destroy:
        删除任务明细
    create:
        创建任务明细
    partial_update:
        更新部分任务明细
    """
    serializer_class = JobOrderDetailsSerializer
    filter_class = JobOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return JobOrderDetails.objects.none()
        user = self.request.user
        queryset = JobOrderDetails.objects.filter(order__department=user.department, order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = JobOrderDetailsFilter(params)
        serializer = JobOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = JobOrderDetailsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = JobOrderDetails.objects.filter(id__in=order_ids, order_status=1)
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
                if not re.match(r'^[SFYT0-9]+$', obj.track_id):
                    obj.mistake_tag = 1
                    obj.save()
                    data["error"].append("%s 快递单号错误" % obj.track_id)
                    n -= 1
                    continue

                obj.order_status = 2
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
    def file_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = JobOrderDetails.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        log_file_names = []
        if files:
            prefix = "ut3s1/workorder/joborderdetails"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                file_order = JODFiles()
                file_order.url = obj["url"]
                file_order.name = obj["name"]
                log_file_names.append(obj["name"])
                file_order.suffix = obj["suffix"]
                file_order.workorder = work_order
                file_order.creator = request.user
                file_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
            logging(work_order, user, LogJobOrderDetails, "上传：%s" % str(log_file_names))
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class JobOrderDetailsManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细
    list:
        返回任务明细
    update:
        更新任务明细
    destroy:
        删除任务明细
    create:
        创建任务明细
    partial_update:
        更新部分任务明细
    """
    serializer_class = JobOrderDetailsSerializer
    filter_class = JobOrderDetailsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return JobOrderDetails.objects.none()
        user = self.request.user
        queryset = JobOrderDetails.objects.filter(order__department=user.department, order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["is_forward"] = user.is_our
        f = JobOrderDetailsFilter(params)
        serializer = JobOrderDetailsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = JobOrderDetails.objects.filter(id=id)[0]
        ret = getlogs(instance, LogJobOrderDetails)
        return Response(ret)

    @action(methods=['patch'], detail=False)
    def get_file_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = JobOrderDetails.objects.filter(id=id)[0]
        ret = getfiles(instance, JODFiles)
        return Response(ret)


class JODFilesViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定任务明细文档
    list:
        返回任务明细文档
    update:
        更新任务明细文档
    destroy:
        删除任务明细文档
    create:
        创建任务明细文档
    partial_update:
        更新部分任务明细文档
    """
    serializer_class = JODFilesSerializer
    filter_class = JODFilesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['manualorder.view_manualorder']
    }

    def get_queryset(self):
        if not self.request:
            return JODFiles.objects.none()
        queryset = JODFiles.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def delete_file(self, request):
        id = request.data.get("id", None)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if id:
            files_order = JODFiles.objects.filter(id=id, creator=user, is_delete=False)
            if files_order.exists():
                file_order = files_order[0]
                file_order.is_delete = 1
                file_order.save()
                data["successful"] += 1
                logging(file_order.workorder, user, LogJobOrderDetails, "删除文档：%s" % file_order.name)
            else:
                data["false"] += 1
                data["error"].append("只有创建者才有删除权限")
        else:
            data["false"] += 1
            data["error"].append("没有找到删除对象")
        return Response(data)












