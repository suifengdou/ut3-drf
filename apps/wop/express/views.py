import re, math
import datetime
import pandas as pd
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import ExpressWorkOrder, EWOPhoto, LogExpressOrder
from .serializers import ExpressWorkOrderSerializer, EWOPhotoSerializer
from .filters import ExpressWorkOrderFilter, EWOPhotoFilter
from ut3.settings import EXPORT_TOPLIMIT
from apps.base.company.models import Company
import oss2
from ut3.settings import OSS_CONFIG
from itertools import islice
from apps.utils.oss.aliyunoss import AliyunOSS
from apps.utils.logging.loggings import getlogs, logging


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
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = ExpressWorkOrder.objects.filter(order_status=1, is_forward=user.is_our).order_by("-id")
        else:
            queryset = ExpressWorkOrder.objects.filter(company=user.company, order_status=1, is_forward=user.is_our).order_by("-id")
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
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["is_forward"] = user.is_our
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
                if not re.match(r'^[SFYT0-9]+$', obj.track_id):
                    obj.mistake_tag = 1
                    obj.save()
                    data["error"].append("%s 快递单号错误" % obj.track_id)
                    n -= 1
                    continue

                obj.order_status = 2
                obj.save()
                logging(obj, user, LogExpressOrder, "提交工单")
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

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)
            columns_key_ori = df.columns.values.tolist()
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注", "是否返回", "返回单号"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
                "是否返回": "is_return",
                "返回单号": "return_express_id",
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
            _ret_verify_field = ExpressWorkOrder.verify_mandatory(result_columns)
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
            "截单退回": 1,
            "无人收货": 2,
            "客户拒签": 3,
            "修改地址": 4,
            "催件派送": 5,
            "虚假签收": 6,
            "丢件破损": 7,
            "其他异常": 8
        }
        return_tag_list = {
            "是": True,
        }
        user = request.user

        for row in resource:

            order_fields_common = ["track_id", "category", "company", "information", "memo"]
            order_fields_return = ["track_id", "category", "company", "information", "is_return", "return_express_id", "memo"]
            row["category"] = category_list.get(row["category"], None)
            row["is_return"] = return_tag_list.get(row["is_return"], False)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递工单已存在" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = ExpressWorkOrder()
            order.is_forward = user.is_our
            if row["is_return"]:
                order_fields = order_fields_return
            else:
                order_fields = order_fields_common
            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())
            order.return_express_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.return_express_id).strip())
            try:
                order.creator = user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["track_id"])
                report_dic["false"] += 1

        return report_dic

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = ExpressWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/express"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = EWOPhoto()
                photo_order.url = obj["url"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
                logging(work_order, user, LogExpressOrder, "上传图片")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
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
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        user = self.request.user
        is_forward = bool(1 - user.is_our)
        if not self.request:
            return ExpressWorkOrder.objects.none()
        if user.is_our:
            queryset = ExpressWorkOrder.objects.filter(order_status=2, is_forward=is_forward).order_by("id")
        else:
            queryset = ExpressWorkOrder.objects.filter(order_status=2, is_forward=is_forward, company=user.company).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        params["is_forward"] = bool(1 - user.is_our)
        if not user.is_our:
            params["company"] = user.company
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["is_forward"] = bool(1 - user.is_our)
        if not user.is_our:
            params["company"] = user.company
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=2, is_forward=bool(1 - user.is_our))
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def batchtext(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        update_data = params.pop("data", None)
        if not update_data:
            raise serializers.ValidationError("批量修改内容为空！")
        batch_list = self.get_handle_list(params)
        n = len(batch_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        keys = list(update_data.keys())
        if len(keys) != 1:
            raise serializers.ValidationError("批量修改内容错误！")
        key = str(keys[0])
        current_time = datetime.datetime.now().date()
        update_data[key] = f"{update_data[key]}{{{user.username}-{current_time}}}"
        if n:
            for obj in batch_list:
                origin_data = getattr(obj, key, None)
                if origin_data:
                    update_value = "%s %s" % (origin_data, update_data[key])
                else:
                    update_value = update_data[key]
                setattr(obj, key, update_value)
                obj.save()
                logging(obj, user, LogExpressOrder, "{%s}:%s替换为%s" % (key, origin_data, update_data[key]))
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(batch_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_return(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if n:
            check_list.update(is_return=True)
            for obj in check_list:
                logging(obj, user, LogExpressOrder, "批量设置返回")
        else:
            raise serializers.ValidationError("没有可处理的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_return_trackid(self, request, *args, **kwargs):
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
                obj.return_express_id = obj.track_id
                try:
                    obj.save()
                    data["successful"] += 1
                    logging(obj, user, LogExpressOrder, "批量设置原单号退回")
                except Exception as e:
                    data["error"].append(e)
        else:
            raise serializers.ValidationError("没有可处理的单据！")
        data["false"] = len(check_list) - data["successful"]
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_lossing(self, request, *args, **kwargs):
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
            check_list.update(process_tag=7)
            for obj in check_list:
                logging(obj, user, LogExpressOrder, "设置丢件标记")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def batch_sign(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        process_tag = params.pop("set_process_tag", None)
        if not process_tag:
            raise serializers.ValidationError({"系统错误": "未传入正确的标记代码！"})
        sign_list = self.get_handle_list(params)
        n = len(sign_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        SIGN_LIST = {
            0: '清标记',
            1: '待截单',
            2: '签复核',
            3: '改地址',
            4: '催派查',
            5: '丢件核',
            6: '纠纷中',
            7: '需理赔',
            8: '其他类',
        }
        if n:
            process_tag_name = SIGN_LIST.get(process_tag, None)
            for obj in sign_list:
                obj.process_tag = process_tag
                obj.save()
                logging(obj, user, LogExpressOrder, f'批量设置标记为：{process_tag_name}')
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def recover(self, request, *args, **kwargs):
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
            check_list.update(process_tag=0)
            for obj in check_list:
                logging(obj, user, LogExpressOrder, "恢复标记为默认")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

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
                if not obj.suggestion:
                    obj.mistake_tag = 2
                    obj.save()
                    data["error"].append("%s 处理意见为空" % obj.track_id)
                    n -= 1
                    continue
                if obj.is_return:
                    if not obj.return_express_id:
                        obj.mistake_tag = 3
                        obj.save()
                        data["error"].append("%s 返回的单据无返回单号" % obj.track_id)
                        n -= 1
                        continue
                if obj.is_losing:
                    if obj.process_tag != 7:
                        obj.mistake_tag = 4
                        obj.save()
                        data["error"].append("%s 理赔必须设置需理赔才可以审核" % obj.track_id)
                        n -= 1
                        continue
                obj.submit_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(obj.updated_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(obj.submit_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                obj.services_interval = math.floor(total_seconds / 60)
                obj.servicer = request.user.username
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogExpressOrder, "处理完成单据")
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
                if not obj.rejection:
                    obj.mistake_tag =5
                    obj.save()
                    data["error"].append("%s 驳回原因为空" % obj.track_id)
                    n -= 1
                    continue
                obj.order_status = 1
                obj.save()
                logging(obj, user, LogExpressOrder, "驳回单据到创建")

        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        user = request.user
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = ExpressWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/express"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = EWOPhoto()
                photo_order.url = obj["url"]
                photo_order.workorder = work_order
                photo_order.creator = user.username
                photo_order.save()
                logging(work_order, user, LogExpressOrder, "上传图片成功")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class EWOExecuteViewset(viewsets.ModelViewSet):
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
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = ExpressWorkOrder.objects.filter(order_status=3, is_forward=user.is_our).order_by("id")
        else:
            queryset = ExpressWorkOrder.objects.filter(company=user.company, order_status=3, is_forward=user.is_our).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 3
        params["is_forward"] = user.is_our
        if not user.is_our:
            params["company"] = user.company
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        params["is_forward"] = user.is_our
        if not user.is_our:
            params["company"] = user.company
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=3, is_forward=user.is_our)
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
                if not obj.feedback:
                    obj.mistake_tag = 6
                    obj.save()
                    data["error"].append("%s  无执行内容, 不可以审核" % obj.track_id)
                    n -= 1
                    continue
                if obj.is_return:
                    if not obj.return_express_id:
                        obj.mistake_tag = 3
                        obj.save()
                        data["error"].append("%s 返回的单据无返回单号" % obj.track_id)
                        n -= 1
                        continue
                if obj.is_losing:
                    if obj.process_tag != 7:
                        obj.mistake_tag = 4
                        obj.save()
                        data["error"].append("%s 理赔必须设置需理赔才可以审核" % obj.track_id)
                        n -= 1
                        continue
                    if obj.indemnification == 0:
                        obj.mistake_tag = 7
                        obj.save()
                        data["error"].append("%s 理赔必须设置金额" % obj.track_id)
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
                obj.handle_interval = math.floor(total_seconds / 60)
                obj.handler = request.user.username
                obj.order_status = 4
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogExpressOrder, "单据执行完毕")
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
                if not obj.rejection:
                    obj.mistake_tag =5
                    obj.save()
                    data["error"].append("%s 驳回原因为空" % obj.track_id)
                    n -= 1
                    continue
                obj.order_status = 2
                obj.save()
                logging(obj, user, LogExpressOrder, "单据驳回到待处理")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def batchtext(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        update_data = params.pop("data", None)
        if not update_data:
            raise serializers.ValidationError("批量修改内容为空！")
        batch_list = self.get_handle_list(params)
        n = len(batch_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        keys = list(update_data.keys())
        if len(keys) != 1:
            raise serializers.ValidationError("批量修改内容错误！")
        key = str(keys[0])
        current_time = datetime.datetime.now().date()
        update_data[key] = f"{update_data[key]}{{{user.username}-{current_time}}}"
        if n:
            for obj in batch_list:
                origin_data = getattr(obj, key, None)
                if origin_data:
                    update_value = "%s %s" % (origin_data, update_data[key])
                else:
                    update_value = update_data[key]
                setattr(obj, key, update_value)
                obj.save()
                logging(obj, user, LogExpressOrder, "{%s}:%s替换为%s" % (key, origin_data, update_data[key]))
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(batch_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def batch_sign(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        process_tag = params.pop("set_process_tag", None)
        if not process_tag:
            raise serializers.ValidationError({"系统错误": "未传入正确的标记代码！"})
        sign_list = self.get_handle_list(params)
        n = len(sign_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        SIGN_LIST = {
            0: '清标记',
            1: '待截单',
            2: '签复核',
            3: '改地址',
            4: '催派查',
            5: '丢件核',
            6: '纠纷中',
            7: '需理赔',
            8: '其他类',
        }
        if n:
            process_tag_name = SIGN_LIST.get(process_tag, None)
            for obj in sign_list:
                obj.process_tag = process_tag
                obj.save()
                logging(obj, user, LogExpressOrder, f'批量设置标记为：{process_tag_name}')
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_feedback(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        current_time = datetime.datetime.now()
        user = request.user.username
        feedback_content = "收到处理意见，按流程执行完成。{%s-%s}" % (str(user), str(current_time)[:19])
        if n:
            for obj in check_list:
                if obj.feedback:
                    obj.feedback = '%s~%s' % (obj.feedback, feedback_content)
                else:
                    obj.feedback = feedback_content
                try:
                    obj.save()
                    data["successful"] += 1
                except Exception as e:
                    data["error"].append(e)
        else:
            raise serializers.ValidationError("没有可处理的单据！")
        data["false"] = len(check_list) - data["successful"]
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_return(self, request, *args, **kwargs):
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
            check_list.update(is_return=True)
            for obj in check_list:
                logging(obj, user, LogExpressOrder, "批量设置返回")
        else:
            raise serializers.ValidationError("没有可处理的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_return_trackid(self, request, *args, **kwargs):
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
                obj.return_express_id = obj.track_id
                try:
                    obj.save()
                    data["successful"] += 1
                    logging(obj, user, LogExpressOrder, "批量原单退回")
                except Exception as e:
                    data["error"].append(e)
        else:
            raise serializers.ValidationError("没有可处理的单据！")
        data["false"] = len(check_list) - data["successful"]
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
        "GET": ['express.view_check_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        queryset = ExpressWorkOrder.objects.filter(order_status=4).order_by("id")
        for order in queryset:
            if not order.check_time:
                order.handling_status = 0
                order.save()
                continue
            else:
                today_date = datetime.datetime.now().date()
                check_date = order.check_time.date()
                if check_date <= today_date:
                    order.handling_status = 0
                    order.save()
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 4
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def set_appointment(self, request, *args, **kwargs):
        user = request.user
        days = request.data.get("days", None)
        id = request.data.get("id", None)
        today = datetime.datetime.now()
        data = {"successful": 0}
        if all([days, id]):
            order = ExpressWorkOrder.objects.filter(id=id)[0]
            if days == 1:
                order.check_time = today + datetime.timedelta(days=1)
            else:
                order.check_time = today + datetime.timedelta(days=3)
            order.handling_status = 1
            order.save()
            data["successful"] = 1
            logging(order, user, LogExpressOrder, "向后延迟检查时间")

        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_recover(self, request, *args, **kwargs):
        user = request.user
        id = request.data.get("id", None)
        today = datetime.datetime.now()
        data = {"successful": 0}
        if id:
            order = ExpressWorkOrder.objects.filter(id=id)[0]
            order.check_time = today
            order.handling_status = 0
            order.save()
            data["successful"] = 1
            logging(order, user, LogExpressOrder, "重置延迟时间到当前")
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 4
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=4)
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
            for order in check_list:
                if order.is_losing:
                    order.order_status = 5
                else:
                    order.order_status = 6
                order.save()
                logging(order, user, LogExpressOrder, "复核完成单据")
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
                obj.order_status = 3
                obj.save()
                logging(obj, user, LogExpressOrder, "驳回单据到待执行")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
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
        "GET": ['express.view_audit_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        queryset = ExpressWorkOrder.objects.filter(order_status=5).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 5
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 5
        if all_select_tag:
            handle_list = ExpressWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ExpressWorkOrder.objects.filter(id__in=order_ids, order_status=5)
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
            check_list.update(order_status=6)
            for obj in check_list:
                logging(obj, user, LogExpressOrder, "财审完成")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
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
                obj.order_status = 4
                obj.save()
                logging(obj, user, LogExpressOrder, "驳回单据到复核")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
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
        "GET": ['express.view_expressworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ExpressWorkOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = ExpressWorkOrder.objects.all().order_by("-id")
        else:
            queryset = ExpressWorkOrder.objects.filter(company=user.company).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_our:
            request.data["company"] = user.company
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ExpressWorkOrderFilter(params)
        serializer = ExpressWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = ExpressWorkOrder.objects.filter(id=id)[0]
        ret = getlogs(instance, LogExpressOrder)
        return Response(ret)


class EWOPhotoViewset(viewsets.ModelViewSet):
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
    serializer_class = EWOPhotoSerializer
    filter_class = EWOPhotoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)

    def get_queryset(self):
        if not self.request:
            return EWOPhoto.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = EWOPhoto.objects.all().order_by("id")
        else:
            queryset = EWOPhoto.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def delete_photo(self, request):
        id = request.data.get("id", None)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        user = request.user
        if id:
            photo_order = EWOPhoto.objects.filter(id=id, creator=user.username, is_delete=False)
            if photo_order.exists():
                photo_order = photo_order[0]
                photo_order.is_delete = 1
                photo_order.save()
                data["successful"] += 1
                logging(photo_order.workorder, user, LogExpressOrder, "删除图片")
            else:
                data["false"] += 1
                data["error"].append("只有创建者才有删除权限")
        else:
            data["false"] += 1
            data["error"].append("没有找到删除对象")
        return Response(data)


