import re, math
import datetime
import pandas as pd
from functools import reduce
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import OriSatisfactionWorkOrder, OSWOFiles, SatisfactionWorkOrder, SWOProgress, SWOPFiles, ServiceWorkOrder, InvoiceWorkOrder, IWOGoods, CheckInvoice
from .serializers import OriSatisfactionWorkOrderSerializer, OSWOFilesSerializer, SWOSerializer, \
    SWOProgressSerializer, ServiceWorkOrderSerializer, InvoiceWorkOrderSerializer, SWOPFilesSerializer
from .filters import OriSatisfactionWorkOrderFilter, OSWOFilesFilter, SWOFilter, SWOProgressFilter, \
    ServiceWorkOrderFilter, InvoiceWorkOrderFilter, SWOPFilesFilter
from ut3.settings import EXPORT_TOPLIMIT
from apps.base.company.models import Company
from apps.crm.customers.models import Customer, ContactAccount, Satisfaction, Money, Interaction
from apps.crm.vipwechat.models import VIPWechat
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.base.shop.models import Shop
from apps.utils.oss.aliyunoss import AliyunOSS
from apps.utils.geography.tools import PickOutAdress
from ut3.settings import EXPORT_TOPLIMIT


# 原始体验单创建
class OSWOCreateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = OriSatisfactionWorkOrderSerializer
    filter_class = OriSatisfactionWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_orisatisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return OriSatisfactionWorkOrder.objects.none()
        user = self.request.user
        queryset = OriSatisfactionWorkOrder.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriSatisfactionWorkOrderFilter(params)
        serializer = OriSatisfactionWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = OriSatisfactionWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriSatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status != 0:
                        obj.mistake_tag = 1
                        data["error"].append("%s 重复提交，点击修复工单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                if vipwechat:
                    order.is_friend = True
                    order.cs_wechat = vipwechat.cs_wechat
                    order.specialist = vipwechat.specialist
                    order.process_tag = 4
                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status__in=[1, 2, 3]).exists():
                        obj.mistake_tag = 2
                        data["error"].append("%s 已存在未完结工单，联系处理同学追加问题" % obj.address)
                        n -= 1
                        obj.save()
                        continue
                    elif _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo", "demand",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "receiver"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始化执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
                    obj.save()
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
    def fix(self, request, *args, **kwargs):
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
                if obj.mistake_tag != 1:
                    data["error"].append("%s 非重复提交状态，不可修复" % obj.order_id)
                    n -= 1
                    continue

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status > 1:
                        obj.mistake_tag = 7
                        data["error"].append("%s 体验单已操作无法修复，驳回体验单到待领取重复递交后再修复" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer
                if vipwechat:
                    order.is_friend = True
                    order.cs_wechat = vipwechat.cs_wechat
                    order.specialist = vipwechat.specialist
                    order.process_tag = 4
                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    continue
                progress_order.swopfiles_set.all().delete()
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 原始体验单综合处理
class OSWOHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = OriSatisfactionWorkOrderSerializer
    filter_class = OriSatisfactionWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_handle_orisatisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return OriSatisfactionWorkOrder.objects.none()
        user = self.request.user
        queryset = OriSatisfactionWorkOrder.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriSatisfactionWorkOrderFilter(params)
        serializer = OriSatisfactionWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriSatisfactionWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriSatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status != 0:
                        obj.mistake_tag = 1
                        data["error"].append("%s 重复提交，点击修复工单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer
                if vipwechat:
                    order.is_friend = True
                    order.cs_wechat = vipwechat.cs_wechat
                    order.specialist = vipwechat.specialist
                    order.process_tag = 4
                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status__in=[1, 2, 3]).exists():
                        obj.mistake_tag = 2
                        data["error"].append("%s 已存在未完结工单，联系处理同学追加问题" % obj.address)
                        n -= 1
                        obj.save()
                        continue
                    elif _q_swo.filter(order_status=4).exists():
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo", "demand",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "receiver"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始化执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
                    obj.save()
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
    def fix(self, request, *args, **kwargs):
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
                if obj.mistake_tag != 1:
                    data["error"].append("%s 非重复提交状态，不可修复" % obj.order_id)
                    n -= 1
                    continue

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status > 1:
                        obj.mistake_tag = 7
                        data["error"].append("%s 体验单已操作无法修复，驳回体验单到待领取重复递交后再修复" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer
                if vipwechat:
                    order.is_friend = True
                    order.cs_wechat = vipwechat.cs_wechat
                    order.specialist = vipwechat.specialist
                    order.process_tag = 4
                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    continue
                progress_order.swopfiles_set.all().delete()
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 原始体验单查询
class OSWOManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单管理
    list:
        返回原始体验单管理
    update:
        更新原始体验单管理
    destroy:
        删除原始体验单管理
    create:
        创建原始体验单管理
    partial_update:
        更新部分原始体验单管理
    """
    serializer_class = OriSatisfactionWorkOrderSerializer
    filter_class = OriSatisfactionWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_orisatisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return OriSatisfactionWorkOrder.objects.none()
        user = self.request.user
        queryset = OriSatisfactionWorkOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriSatisfactionWorkOrderFilter(params)
        serializer = OriSatisfactionWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


# 原始体验单文档管理
class OSWOFilesViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单文档
    list:
        返回原始体验单文档
    update:
        更新原始体验单文档
    destroy:
        删除原始体验单文档
    create:
        创建原始体验单文档
    partial_update:
        更新部分原始体验单文档
    """
    serializer_class = OSWOFilesSerializer
    filter_class = OSWOFilesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_orisatisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return OSWOFiles.objects.none()
        queryset = OSWOFiles.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OSWOFilesFilter(params)
        serializer = OSWOFilesSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = OSWOFilesFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriSatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)


# 体验单领取
class SWOHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定体验单领取
    list:
        返回体验单领取
    update:
        更新体验单领取
    destroy:
        删除体验单领取
    create:
        创建体验单领取
    partial_update:
        更新部分体验单领取
    """
    serializer_class = SWOSerializer
    filter_class = SWOFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_satisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return SatisfactionWorkOrder.objects.none()
        queryset = SatisfactionWorkOrder.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = SWOFilter(params)
        serializer = SWOSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = SWOFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = SatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status != 0:
                        obj.mistake_tag = 1
                        data["error"].append("%s 重复提交，点击修复工单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status__in=[1, 2, 3]).exists():
                        obj.mistake_tag = 2
                        data["error"].append("%s 已存在未完结工单，联系处理同学追加问题" % obj.address)
                        n -= 1
                        obj.save()
                        continue
                    elif _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始化执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
                    obj.save()
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
    def take_over(self, request, *args, **kwargs):
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }

        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        user = request.user
        _all_specialist = user.specialist_set.all()
        myspecialist = _all_specialist.filter(is_default=True)
        if myspecialist.exists():
            specialist = myspecialist[0]
        else:
            data["false"] = n
            data["error"].append("你没有默认的专属客服账号，不可以领取任务")
            return Response(data)

        if n:
            for obj in check_list:
                if obj.specialist and obj.is_friend:
                    if obj.specialist not in _all_specialist:
                        if obj.process_tag != 5:
                            data["error"].append("%s 此用户已经存在专属客服，需要专属客服领取, 或者特设单据" % obj.address)
                            n -= 1
                            obj.save()
                            continue
                else:
                    obj.specialist = specialist
                obj.handler = request.user.username
                obj.handle_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(obj.update_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(obj.handle_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                obj.handle_interval = math.floor(total_seconds / 60)

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
            for obj in reject_list:
                obj.ori_order.order_status = 1
                obj.ori_order.save()
                obj.order_status = 0
                obj.swoprogress_set.all().delete()
                obj.save()
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
            set_list.update(process_tag=5)
        else:
            raise serializers.ValidationError("没有可设置的单据！")
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = SWOProgress.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/swoprogressfile"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = SWOPFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 体验单个人处理界面
class SWOMyselfViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定体验单执行
    list:
        返回体验单执行
    update:
        更新体验单执行
    destroy:
        删除体验单执行
    create:
        创建体验单执行
    partial_update:
        更新部分体验单执行
    """
    serializer_class = SWOSerializer
    filter_class = SWOFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_satisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return SatisfactionWorkOrder.objects.none()
        user = self.request.user
        queryset = SatisfactionWorkOrder.objects.filter(order_status=2, handler=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = SWOFilter(params)
        serializer = SWOSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["creator"] = user.username
        if all_select_tag:
            handle_list = SWOFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = SatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=2)
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
                if obj.stage != 5:
                    obj.mistake_tag = 3
                    data["error"].append("%s 体验单未完成不可审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                if obj.is_friend:
                    vipwechat = VIPWechat()
                    vipwechat.specialist = obj.specialist
                    vipwechat.customer = obj.customer
                    vipwechat.cs_wechat = obj.cs_wechat
                    vipwechat.memo = "来源于 %s" % str(obj.order_id)
                    try:
                        vipwechat.creator = request.user.username
                        vipwechat.save()
                    except Exception as e:
                        pass
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
                obj.order_status = 1
                obj.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = SWOProgress.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/swoprogressfile"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = SWOPFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    @action(methods=['patch'], detail=False)
    def create_service(self, request, *args, **kwargs):
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
                try:
                    order = obj.serviceworkorder
                    if order.order_status < 2:
                        order.order_status = 1
                    else:
                        obj.mistake_tag = 1
                        data["error"].append("%s 已存在已执行服务单，不可创建" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                except Exception as e:
                    order = ServiceWorkOrder()


                order_info_fields = ["title", "nickname", "customer", "receiver", "address", "mobile", "province",
                                     "city", "district", "demand"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))
                order.title = '%s-服务单' % order.title



                try:
                    order.swo_order = obj
                    order.creator = request.user.username
                    order.save()
                    today = datetime.datetime.now()
                    today = re.sub('[- :\.]', '', str(today))[:8]
                    number = int(order.id) + 10000000
                    profix = "SS"
                    order.order_id = '%s%s%s' % (profix, today, str(number)[-7:])
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 2
                    data["error"].append("%s 创建服务单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                obj.process_tag = 3
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


# 体验单综合处理界面
class SWOExecuteViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定体验单执行
    list:
        返回体验单执行
    update:
        更新体验单执行
    destroy:
        删除体验单执行
    create:
        创建体验单执行
    partial_update:
        更新部分体验单执行
    """
    serializer_class = SWOSerializer
    filter_class = SWOFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_handler_satisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return SatisfactionWorkOrder.objects.none()
        user = self.request.user
        queryset = SatisfactionWorkOrder.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = SWOFilter(params)
        serializer = SWOSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        params["creator"] = user.username
        if all_select_tag:
            handle_list = SWOFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = SatisfactionWorkOrder.objects.filter(id__in=order_ids, order_status=2)
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
                if obj.stage != 5:
                    obj.mistake_tag = 3
                    data["error"].append("%s 体验单未完成不可审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                if obj.is_friend:
                    vipwechat = VIPWechat()
                    vipwechat.specialist = obj.specialist
                    vipwechat.customer = obj.customer
                    vipwechat.cs_wechat = obj.cs_wechat
                    vipwechat.memo = "来源于 %s" % str(obj.order_id)
                    try:
                        vipwechat.creator = request.user.username
                        vipwechat.save()
                    except Exception as e:
                        pass
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
                obj.order_status = 1
                obj.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = SWOProgress.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/swoprogressfile"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = SWOPFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    @action(methods=['patch'], detail=False)
    def create_service(self, request, *args, **kwargs):
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
                try:
                    order = obj.serviceworkorder
                    if order.order_status < 2:
                        order.order_status = 1
                    else:
                        obj.mistake_tag = 1
                        data["error"].append("%s 已存在已执行服务单，不可创建" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                except Exception as e:
                    order = ServiceWorkOrder()


                order_info_fields = ["title", "nickname", "customer", "name", "address", "smartphone", "province",
                                     "city", "district", "demand"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))
                order.title = '%s-服务单' % order.title



                try:
                    order.swo_order = obj
                    order.creator = request.user.username
                    order.save()
                    today = datetime.datetime.now()
                    today = re.sub('[- :\.]', '', str(today))[:8]
                    number = int(order.id) + 10000000
                    profix = "SS"
                    order.order_id = '%s%s%s' % (profix, today, str(number)[-7:])
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 2
                    data["error"].append("%s 创建服务单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                obj.process_tag = 3
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


# 体验单综合查询
class SWOManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定体验单执行
    list:
        返回体验单执行
    update:
        更新体验单执行
    destroy:
        删除体验单执行
    create:
        创建体验单执行
    partial_update:
        更新部分体验单执行
    """
    serializer_class = SWOSerializer
    filter_class = SWOFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_satisfactionworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return SatisfactionWorkOrder.objects.none()
        queryset = SatisfactionWorkOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = SWOFilter(params)
        serializer = SWOSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)


# 体验执行单创建处理
class SWOPCreateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定进度单
    list:
        返回进度单
    update:
        更新进度单
    destroy:
        删除进度单
    create:
        创建进度单
    partial_update:
        更新部分进度单
    """
    serializer_class = SWOProgressSerializer
    filter_class = SWOProgressFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_swoprogress']
    }

    def get_queryset(self):
        if not self.request:
            return SWOProgress.objects.none()
        user = self.request.user
        queryset = SWOProgress.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = SWOProgressFilter(params)
        serializer = SWOProgressSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = SWOProgressFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = SWOProgress.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status != 0:
                        obj.mistake_tag = 1
                        data["error"].append("%s 重复提交，点击修复工单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status__in=[1, 2, 3]).exists():
                        obj.mistake_tag = 2
                        data["error"].append("%s 已存在未完结工单，联系处理同学追加问题" % obj.address)
                        n -= 1
                        obj.save()
                        continue
                    elif _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始化执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
                    obj.save()
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
            for obj in reject_list:
                obj.ori_order.order_status = 1
                obj.ori_order.save()
                obj.order_status = 0
                obj.swoprogress_set.all().delete()
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def photo_import(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = SWOProgress.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/swoprogressfile"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = SWOPFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 体验进程单文档管理
class SWOPFilesViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单文档
    list:
        返回原始体验单文档
    update:
        更新原始体验单文档
    destroy:
        删除原始体验单文档
    create:
        创建原始体验单文档
    partial_update:
        更新部分原始体验单文档
    """
    serializer_class = SWOPFilesSerializer
    filter_class = SWOPFilesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_swoprogress']
    }

    def get_queryset(self):
        if not self.request:
            return SWOPFiles.objects.none()
        queryset = SWOPFiles.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OSWOFilesFilter(params)
        serializer = SWOPFilesSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = OSWOFilesFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = SWOPFiles.objects.filter(id__in=order_ids, order_status=1)
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
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)


# 服务单处理
class ServiceMyselfViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = ServiceWorkOrderSerializer
    filter_class = ServiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_serviceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ServiceWorkOrder.objects.none()
        user = self.request.user
        queryset = ServiceWorkOrder.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = ServiceWorkOrderFilter(params)
        serializer = ServiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = ServiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ServiceWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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
                all_invoice = obj.invoiceworkorder_set.all()
                if all_invoice.exists():
                    if all_invoice.filter(order_status__in=[1, 2]).exists():
                        obj.mistake_tag = 1
                        data["error"].append("%s 存在未完结发货单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    cost = all_invoice.aggregate(Sum("cost"))["cost__sum"]
                    if cost == 0:
                        obj.mistake_tag = 2
                        data["error"].append("%s 费用为零不可审核" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        obj.cost = cost
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s 不存在费用单不可以审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                obj.swo_order.cost = obj.cost
                obj.swo_order.save()
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
            for obj in reject_list:
                obj.swo_order.process_tag = 0
                obj.swo_order.save()
                obj.order_status = 0
                obj.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


    @action(methods=['patch'], detail=False)
    def create_invoice(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        data = {
            "error": "系统错误联系管理员，无法回传单据ID！"
        }
        return Response(data)


# 服务单综合处理
class ServiceHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = ServiceWorkOrderSerializer
    filter_class = ServiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_serviceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ServiceWorkOrder.objects.none()
        user = self.request.user
        queryset = ServiceWorkOrder.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = ServiceWorkOrderFilter(params)
        serializer = ServiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = ServiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ServiceWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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
                all_invoice = obj.invoiceworkorder_set.all()
                if all_invoice.exist():
                    if all_invoice.filter(order_status__in=[1, 2]).exists():
                        obj.mistake_tag = 1
                        data["error"].append("%s 存在未完结发货单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    cost = all_invoice.aggregate(Sum("cost"))["cost__sum"]
                    if cost == 0:
                        obj.mistake_tag = 2
                        data["error"].append("%s 费用为零不可审核" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        obj.cost = cost
                else:
                    obj.mistake_tag = 3
                    data["error"].append("%s 不存在费用单不可以审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                obj.swo_order.cost = obj.cost
                obj.swo_order.save()
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
            for obj in reject_list:
                obj.swo_order.process_tag = 0
                obj.swo_order.save()
                obj.order_status = 0
                obj.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


    @action(methods=['patch'], detail=False)
    def create_invoice(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        data = {
            "error": "系统错误联系管理员，无法回传单据ID！"
        }
        return Response(data)


# 服务单查询
class ServiceManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = ServiceWorkOrderSerializer
    filter_class = ServiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_serviceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return ServiceWorkOrder.objects.none()
        queryset = ServiceWorkOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = ServiceWorkOrderFilter(params)
        serializer = ServiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = ServiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ServiceWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.smartphone)
                vipwechat = None
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
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
                if obj.mistake_tag != 1:
                    data["error"].append("%s 非重复提交状态，不可修复" % obj.order_id)
                    n -= 1
                    continue

                _q_customer = Customer.objects.filter(name=obj.smartphone)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.smartphone
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status > 1:
                        obj.mistake_tag = 7
                        data["error"].append("%s 体验单已操作无法修复，驳回体验单到待领取重复递交后再修复" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(smartphone=obj.smartphone).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "smartphone", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    continue
                progress_order.swopfiles_set.all().delete()
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
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
            for obj in reject_list:
                obj.swo_order.process_tag = 0
                obj.swo_order.save()
                obj.order_status = 0
                obj.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


    @action(methods=['patch'], detail=False)
    def create_invoice(self, request, *args, **kwargs):
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        data = {
            "error": "系统错误联系管理员，无法回传单据ID！"
        }
        return Response(data)


# 发货单创建
class InvoiceCreateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = InvoiceWorkOrderSerializer
    filter_class = InvoiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_invoiceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return InvoiceWorkOrder.objects.none()
        user = self.request.user
        queryset = InvoiceWorkOrder.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = InvoiceWorkOrderFilter(params)
        serializer = InvoiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = InvoiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = InvoiceWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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
                if not obj.erp_order_id:
                    obj.mistake_tag = 4
                    data["error"].append("%s 无UT单号" % obj.id)
                    n -= 1
                    obj.save()
                    continue
                if not re.match("^[0-9]+$", obj.mobile):
                    obj.mistake_tag = 1
                    data["error"].append("%s 电话错误" % obj.id)
                    n -= 1
                    obj.save()
                    continue

                if not obj.receiver:
                    obj.mistake_tag = 2
                    data["error"].append("%s 无收件人" % obj.id)
                    n -= 1
                    obj.save()
                    continue

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(obj, key_word, _rt_addr.get(key_word, None))

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
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
                if obj.mistake_tag != 1:
                    data["error"].append("%s 非重复提交状态，不可修复" % obj.order_id)
                    n -= 1
                    continue

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status > 1:
                        obj.mistake_tag = 7
                        data["error"].append("%s 体验单已操作无法修复，驳回体验单到待领取重复递交后再修复" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    continue
                progress_order.swopfiles_set.all().delete()
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 发货单审核
class InvoiceCheckViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = InvoiceWorkOrderSerializer
    filter_class = InvoiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_handler_invoiceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return InvoiceWorkOrder.objects.none()
        queryset = InvoiceWorkOrder.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = InvoiceWorkOrderFilter(params)
        serializer = InvoiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = InvoiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = InvoiceWorkOrder.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        shop = Shop.objects.filter(name='小狗吸尘器官方旗舰店')[0]
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                try:
                    if obj.checkinvoice:
                        obj.mistake_tag = 9
                        data["error"].append("%s 不可重复递交" % obj.erp_order_id)
                        n -= 1
                        obj.save()
                        continue
                except Exception as e:
                    pass
                _q_manul = ManualOrder.objects.filter(erp_order_id=obj.erp_order_id)
                if _q_manul.exists():
                    order = _q_manul[0]
                    if order.order_status < 2:
                        order.order_status = 1
                    else:
                        obj.mistake_tag = 5
                        data["error"].append("%s 已存在已发货订单" % obj.erp_order_id)
                        n -= 1
                        obj.save()
                        continue
                else:
                    order = ManualOrder()
                order_info_fields = ["order_id", "receiver", "mobile", "address", "nickname", "memo", "erp_order_id",
                                     "province", "city", "district", "creator", "department"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                order.shop = shop
                order.order_category = 3

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 6
                    data["error"].append("%s 创建手工单出错" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.mogoods_set.all().delete()
                error_tag = 0
                all_goods_details = obj.iwogoods_set.all()
                if not all_goods_details.exists():
                    obj.mistake_tag = 6
                    data["error"].append("%s 无货品不可审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                goods_expense = all_goods_details.filter(category__in=[1, 3])
                if goods_expense.exists():
                    expense_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_expense)))
                    expense = reduce(lambda x, y: x + y, expense_list)
                else:
                    expense = 0
                goods_revenue = all_goods_details.filter(category__in=[2, 4])
                if goods_revenue.exists():
                    revenue_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_revenue)))
                    revenue = reduce(lambda x, y: x + y, revenue_list)
                else:
                    revenue = 0
                obj.cost = round(float(expense) - float(revenue), 2)
                quantity_list = list(map(lambda x: int(x.quantity), list(all_goods_details)))
                obj.quantity = reduce(lambda x, y: x + y, quantity_list)
                for goods_detail in all_goods_details:
                    if goods_detail.category == 1:
                        mo_goods = MOGoods()
                        mo_goods.manual_order = order
                        mo_goods.goods_id = goods_detail.goods_name.goods_id
                        mo_goods.quantity = goods_detail.quantity
                        mo_goods.goods_name = goods_detail.goods_name
                        mo_goods.creator = order.creator
                        try:
                            mo_goods.save()
                        except Exception as e:
                            error_tag = 1
                            break
                if error_tag:
                    obj.mistake_tag = 7
                    data["error"].append("%s 创建手工单货品出错" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                try:
                    check_invoice = CheckInvoice()
                    check_invoice.invoice = obj
                    check_invoice.swo_order = obj.swo_order
                    check_invoice.cost = obj.cost
                    check_invoice.quantity = obj.quantity
                    check_invoice.creator = request.user.username
                    check_invoice.save()
                except Exception as e:
                    obj.mistake_tag = 9
                    data["error"].append("%s 不可重复递交" % obj.erp_order_id)
                    n -= 1
                    obj.save()
                    continue
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
                obj.swo_order.cost = obj.swo_order.cost + obj.cost
                obj.swo_order.quantity = obj.swo_order.quantity + obj.quantity
                obj.swo_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        shop = Shop.objects.filter(name='小狗吸尘器官方旗舰店')[0]
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.mistake_tag != 9:
                    obj.mistake_tag = 9
                    data["error"].append("%s 只能修复错误为：重复递交订单" % obj.erp_order_id)
                    n -= 1
                    obj.save()
                    continue
                _q_manul = ManualOrder.objects.filter(erp_order_id=obj.erp_order_id)
                if _q_manul.exists():
                    order = _q_manul[0]
                    if order.order_status < 2:
                        order.order_status = 1
                    else:
                        obj.mistake_tag = 5
                        data["error"].append("%s 存在已发货订单" % obj.erp_order_id)
                        n -= 1
                        obj.save()
                        continue
                else:
                    order = ManualOrder()
                order_info_fields = ["order_id", "receiver", "mobile", "address", "nickname", "memo", "erp_order_id",
                                     "province", "city", "district", "creator", "department"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                order.shop = shop
                order.order_category = 3

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 6
                    data["error"].append("%s 创建手工单出错" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.mogoods_set.all().delete()
                error_tag = 0
                all_goods_details = obj.iwogoods_set.all()
                if not all_goods_details.exists():
                    obj.mistake_tag = 6
                    data["error"].append("%s 无货品不可审核" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                goods_expense = all_goods_details.filter(category__in=[1, 3])
                if goods_expense.exists():
                    expense_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_expense)))
                    expense = reduce(lambda x, y: x + y, expense_list)
                else:
                    expense = 0
                goods_revenue = all_goods_details.filter(category__in=[2, 4])
                if goods_revenue.exists():
                    revenue_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_revenue)))
                    revenue = reduce(lambda x, y: x + y, revenue_list)
                else:
                    revenue = 0
                obj.cost = round(float(expense) - float(revenue), 2)
                quantity_list = list(map(lambda x: int(x.quantity), list(all_goods_details)))
                obj.quantity = reduce(lambda x, y: x + y, quantity_list)
                for goods_detail in all_goods_details:
                    if goods_detail.category == 1:
                        mo_goods = MOGoods()
                        mo_goods.manual_order = order
                        mo_goods.goods_id = goods_detail.goods_name.goods_id
                        mo_goods.quantity = goods_detail.quantity
                        mo_goods.goods_name = goods_detail.goods_name
                        mo_goods.creator = order.creator
                        try:
                            mo_goods.save()
                        except Exception as e:
                            error_tag = 1
                            break
                if error_tag:
                    obj.mistake_tag = 7
                    data["error"].append("%s 创建手工单货品出错" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue

                obj.order_status = 3
                obj.mistake_tag = 0
                obj.save()
                swo_all_invoice = obj.swo_order.checkinvoice_set.all()
                swo_cost = swo_all_invoice.aggregate(Sum("cost"))["cost__sum"]
                swo_quantiy = swo_all_invoice.aggregate(Sum("quantity"))["quantity__sum"]
                obj.swo_order.cost = swo_cost
                obj.swo_order.quantity = swo_quantiy
                obj.swo_order.save()
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


# 发货单查询
class InvoiceManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始体验单创建
    list:
        返回原始体验单创建
    update:
        更新原始体验单创建
    destroy:
        删除原始体验单创建
    create:
        创建原始体验单创建
    partial_update:
        更新部分原始体验单创建
    """
    serializer_class = InvoiceWorkOrderSerializer
    filter_class = InvoiceWorkOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['satisfaction.view_invoiceworkorder']
    }

    def get_queryset(self):
        if not self.request:
            return InvoiceWorkOrder.objects.none()
        queryset = InvoiceWorkOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        user = self.request.user
        request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = InvoiceWorkOrderFilter(params)
        serializer = InvoiceWorkOrderSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = InvoiceWorkOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = InvoiceWorkOrder.objects.filter(id__in=order_ids, order_status=1)
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

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status != 0:
                        obj.mistake_tag = 1
                        data["error"].append("%s 重复提交，点击修复工单" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status__in=[1, 2, 3]).exists():
                        obj.mistake_tag = 2
                        data["error"].append("%s 已存在未完结工单，联系处理同学追加问题" % obj.address)
                        n -= 1
                        obj.save()
                        continue
                    elif _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    obj.save()
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo", "demand",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始化执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    obj.save()
                    continue
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
                    obj.save()
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
    def fix(self, request, *args, **kwargs):
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
                if obj.mistake_tag != 1:
                    data["error"].append("%s 非重复提交状态，不可修复" % obj.order_id)
                    n -= 1
                    continue

                _q_customer = Customer.objects.filter(name=obj.mobile)
                vipwechat = None
                if _q_customer.exists():
                    customer = _q_customer[0]
                    try:
                        vipwechat = customer.vipwechat
                    except Exception as e:
                        vipwechat = None
                else:
                    customer = Customer()
                    customer.name = obj.mobile
                    customer.save()

                try:
                    order = obj.satisfactionworkorder
                    if order.order_status > 1:
                        obj.mistake_tag = 7
                        data["error"].append("%s 体验单已操作无法修复，驳回体验单到待领取重复递交后再修复" % obj.order_id)
                        n -= 1
                        obj.save()
                        continue
                    else:
                        order.order_status = 1
                except Exception as e:
                    order = SatisfactionWorkOrder()

                order.customer = customer

                _q_swo = SatisfactionWorkOrder.objects.filter(customer=customer).order_by("-id")
                if _q_swo.exists():
                    if _q_swo.filter(order_status=4).exists():
                        if vipwechat:
                            order.is_friend = True
                            order.cs_wechat = vipwechat.cs_wechat
                            order.specialist = vipwechat.specialist
                        tag_time = _q_swo[0].create_time
                        today = datetime.datetime.now()
                        check_days = (today - tag_time).days
                        if check_days < 31:
                            order.process_tag = 1
                        else:
                            order.process_tag = 2

                _spilt_addr = PickOutAdress(str(obj.address))
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    obj.mistake_tag = 3
                    data["error"].append("%s 地址无法提取省市区" % obj.address)
                    n -= 1
                    continue

                cs_info_fields = ["province", "city", "district", "address"]
                for key_word in cs_info_fields:
                    setattr(order, key_word, _rt_addr.get(key_word, None))

                order_info_fields = ["order_id", "title", "nickname", "mobile", "purchase_time", "memo",
                                     "purchase_interval", "goods_name", "quantity", "m_sn", "name"]
                for key_word in order_info_fields:
                    setattr(order, key_word, getattr(obj, key_word, None))

                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                except Exception as e:
                    obj.mistake_tag = 4
                    data["error"].append("%s 创建体验单错误" % obj.order_id)
                    n -= 1
                    continue
                order.swoprogress_set.all().delete()
                progress_order = SWOProgress()
                progress_order.title = "初始执行进度"
                progress_order.action = "初始化"
                progress_order.content = obj.information
                try:
                    progress_order.order = order
                    progress_order.creator = request.user.username
                    progress_order.save()

                    today = re.sub('[- :\.]', '', str(datetime.datetime.now()))[:8]
                    number = int(progress_order.id) + 10000000
                    profix = "SWOP"
                    progress_order.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
                    progress_order.save()
                except Exception as e:
                    obj.mistake_tag = 5
                    data["error"].append("%s 初始化体验单失败" % obj.order_id)
                    n -= 1
                    continue
                progress_order.swopfiles_set.all().delete()
                all_files = obj.oswofiles_set.all()
                error_tag = 0
                for file in all_files:
                    file_order = SWOPFiles()
                    file_order.workorder = progress_order
                    file_fields = ["name", "suffix", "url"]
                    for key_word in file_fields:
                        setattr(file_order, key_word, getattr(file, key_word, None))
                    try:
                        file_order.creator = request.user.username
                        file_order.save()
                    except Exception as e:
                        error_tag = 1
                        break
                if error_tag:
                    obj.mistake_tag = 6
                    data["error"].append("%s 初始化体验单资料失败" % obj.order_id)
                    n -= 1
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
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
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
            _ret_verify_field = OriSatisfactionWorkOrder.verify_mandatory(result_columns)
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
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = OriSatisfactionWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

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
        files = request.FILES.getlist("files", None)
        id = request.data.get('id', None)
        if id:
            work_order = OriSatisfactionWorkOrder.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/workorder/satisfaction"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = OSWOFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = request.user.username
                photo_order.save()
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)
