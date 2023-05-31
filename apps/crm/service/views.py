import datetime, math
import re
import pandas as pd
from decimal import Decimal
import numpy as np
from django.db.models import Q, Count, Sum, Max, Min, Avg
import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict

from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import OriMaintenance, Maintenance, MaintenanceSummary, LogOriMaintenance, LogOriMaintenanceGoods, \
    LogMaintenance, MaintenanceGoods, OriMaintenanceGoods, LogMaintenanceSummary, LogMaintenanceGoods, MaintenancePartSummary, LogMaintenancePartSummary
from .serializers import OriMaintenanceSerializer, MaintenanceSerializer, MaintenanceSummarySerializer, MaintenanceGoodsSerializer, OriMaintenanceGoodsSerializer, MaintenancePartSummarySerializer
from .filters import OriMaintenanceFilter, MaintenanceFilter, MaintenanceSummaryFilter, MaintenanceGoodsFilter, OriMaintenanceGoodsFilter, MaintenancePartSummaryFilter
from apps.utils.geography.models import Province, City, District
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.base.warehouse.models import Warehouse
from apps.crm.customers.models import Customer, LogCustomer
from apps.utils.logging.loggings import logging, getlogs
from apps.utils.geography.tools import PickOutAdress
from apps.crm.customers.serializers import CustomerLabelSerializer
from apps.crm.labels.models import LabelCategory, Label, LogLabel
from apps.crm.labels.serializers import LabelSerializer
from apps.crm.customerlabel.views import QueryLabel, CreateLabel
from ut3.settings import EXPORT_TOPLIMIT


class OriMaintenanceBeforeViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_orimaintenance']
    }

    except_function_dict = {
        "已取消": "handle_cancel",
        "待审核": "handle_check",
        "逆向待推送": "handle_error",
        "逆向推送失败": "handle_error",
        "待筛单": "handle_error",
        "不可达": "handle_error",
        "待取件": "handle_daily",
        "取件失败": "handle_error",
        "待入库": "handle_daterange",
        "待维修": "handle_multidays",
        "已换新-待打单": "handle_error",
        "待打印": "handle_daily",
        "已打印": "handle_daily",
        "已完成": "handle_completed"
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.filter(order_status=1).exclude(ori_order_status="已完成").order_by("-id")
        today_date = datetime.datetime.now().date()
        for order in queryset:
            if order.check_time:
                check_date = order.check_time.date()
                if check_date <= today_date:
                    order.sign = 0
                    order.check_time = None
                    order.save()
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriMaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriMaintenance.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def batch_sign(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        sign_list = self.get_handle_list(params)
        n = len(sign_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        SIGN_LIST = {
            0: '无',
            1: '处理完毕',
            2: '配件缺货',
            3: '延后处理',
            4: '快递异常',
            5: '特殊问题',
            6: '上报待批',
            7: '其他情况',
        }
        if n:
            standard_order = sign_list.last()
            standard_sign = standard_order.sign
            sign_name = SIGN_LIST.get(standard_sign, None)
            for obj in sign_list:
                obj.sign = standard_sign
                obj.save()

                logging(obj, user, LogOriMaintenance, f'批量设置标记为：{sign_name}')
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
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
        if n:
            for obj in batch_list:
                origin_data = getattr(obj, key, None)
                if origin_data:
                    update_value = "%s %s" % (origin_data, update_data[key])
                else:
                    update_value = update_data[key]
                setattr(obj, key, update_value)
                obj.save()
                logging(obj, user, LogOriMaintenance, "{%s}:%s替换为%s" % (key, origin_data, update_data[key]))
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(batch_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_appointment(self, request, *args, **kwargs):
        user = request.user
        days = request.data.get("days", None)
        id = request.data.get("id", None)
        today = datetime.datetime.now()
        data = {"successful": 0}
        if all([days, id]):
            order = OriMaintenance.objects.filter(id=id)[0]
            if days == 1:
                order.check_time = today + datetime.timedelta(days=1)
            else:
                order.check_time = today + datetime.timedelta(days=3)
            order.sign = 3
            order.save()
            data["successful"] = 1
            logging(order, user, LogOriMaintenance, f"延后{days}天处理")

        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_recover(self, request, *args, **kwargs):
        user = request.user
        id = request.data.get("id", None)
        today = datetime.datetime.now()
        data = {"successful": 0}
        if id:
            order = OriMaintenance.objects.filter(id=id)[0]
            order.check_time = today
            order.sign = 0
            order.check_time = None
            order.save()
            data["successful"] = 1
            logging(order, user, LogOriMaintenance, f"重置延后")
        return Response(data)

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
            check_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def handle_repeated(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        handle_list = self.get_handle_list(params)
        n = len(handle_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in handle_list:
                if not obj.is_repeated:
                    n -= 1
                    data["false"] += 1
                    data["error"].append("非二次维修单据不需要标记")
                    continue
                obj.is_month_filter = True
                obj.save()
                logging(obj, user, LogOriMaintenance, "已标记二次维修")
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
            "保修单号": "order_id",
            "保修单状态": "ori_order_status",
            "收发仓库": "warehouse",
            "处理登记人": "completer",
            "保修类型": "maintenance_type",
            "故障类型": "fault_type",
            "送修类型": "transport_type",
            "序列号": "machine_sn",
            "换新序列号": "new_machine_sn",
            "关联订单号": "send_order_id",
            "保修结束语": "appraisal",
            "关联店铺": "shop",
            "购买时间": "purchase_time",
            "创建时间": "ori_created_time",
            "创建人": "ori_creator",
            "审核时间": "handle_time",
            "审核人": "handler_name",
            "保修完成时间": "finish_time",
            "保修金额": "fee",
            "保修数量": "quantity",
            "最后修改时间": "last_handle_time",
            "客户网名": "buyer_nick",
            "寄件客户姓名": "sender_name",
            "寄件客户手机": "sender_mobile",
            "寄件客户省市县": "sender_area",
            "寄件客户地址": "sender_address",
            "收件物流公司": "send_logistics_company",
            "收件物流单号": "send_logistics_no",
            "收件备注": "send_memory",
            "寄回客户姓名": "return_name",
            "寄回客户手机": "return_mobile",
            "寄回省市区": "return_area",
            "寄回地址": "return_address",
            "寄件指定物流公司": "return_logistics_company",
            "寄件物流单号": "return_logistics_no",
            "寄件备注": "return_memory",
            "保修货品商家编码": "goods_code",
            "保修货品名称": "goods_name",
            "保修货品简称": "goods_abbreviation",
            "故障描述": "description",
            "是否在保修期内": "is_guarantee",
            "收费状态": "charge_status",
            "收费金额": "charge_amount",
            "收费说明": "charge_memory"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["保修单号", "保修单状态", "收发仓库", "处理登记人", "保修类型", "故障类型", "送修类型", "序列号",
                             "换新序列号", "关联订单号", "保修结束语", "关联店铺", "购买时间", "创建时间", "创建人", "审核时间",
                             "审核人", "保修完成时间", "保修金额", "保修数量", "最后修改时间", "客户网名", "寄件客户姓名",
                             "寄件客户手机", "寄件客户省市县", "寄件客户地址", "收件物流公司", "收件物流单号", "收件备注",
                             "寄回客户姓名", "寄回客户手机", "寄回省市区", "寄回地址", "寄件指定物流公司", "寄件物流单号",
                             "寄件备注", "保修货品商家编码", "保修货品名称", "保修货品简称", "故障描述", "是否在保修期内",
                             "收费状态", "收费金额", "收费说明"]

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
            _ret_verify_field = OriMaintenance.verify_mandatory(columns_key)
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

    def save_resources(self, request, resource):
        user = request.user
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            update_sign = 0
            new_order = 0
            if not re.match("^BX", row['order_id']):
                report_dic["discard"] += 1
                report_dic['error'].append(f"{row['order_id']} 单据内容错误")
                continue
            row["machine_sn"] = str(row["machine_sn"]).upper()
            if not re.match("[A-Z0-9]{16}|\d{8}", str(row["machine_sn"])):
                row["machine_sn"] = "unknown"
            _q_repeat_order = OriMaintenance.objects.filter(order_id=row["order_id"])
            if _q_repeat_order.exists():
                order =_q_repeat_order[0]
                if order.ori_order_status in ["已完成", "已取消"]:
                    report_dic["discard"] += 1
                    continue
                else:
                    if order.ori_order_status != row["ori_order_status"]:
                        update_sign = 1
                    else:
                        report_dic["discard"] += 1
            else:
                order = OriMaintenance()
                update_sign = 1
                new_order = 1
            if update_sign:
                # 新版数据库不支持全是0的时间格式。需要处理为空值
                for keyword in ["purchase_time", "ori_created_time", "handle_time", "finish_time", "last_handle_time"]:
                    if row[keyword] == "0000-00-00 00:00:00" or str(row[keyword]) == 'nan':
                        row[keyword] = None
                for keyword in ["ori_created_time", "last_handle_time"]:
                    if isinstance(row[keyword], str):
                        row[keyword] = datetime.datetime.strptime(str(row[keyword]).split(".")[0], "%Y-%m-%d %H:%M:%S")
                # 单据对象的解密标记决定由哪个更新列表进行更新。
                order_fields_partial = ["order_id", "ori_order_status", "warehouse", "completer", "maintenance_type",
                                        "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                                        "appraisal", "shop", "purchase_time", "ori_created_time", "ori_creator", "handle_time",
                                        "handler_name", "finish_time", "fee", "quantity", "buyer_nick", "last_handle_time",
                                        "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                                        "send_logistics_no", "send_memory", "return_logistics_company", "return_logistics_no", "return_memory",
                                        "goods_code", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                                        "charge_status", "charge_amount", "charge_memory"]
                order_fields_entire = ["order_id", "ori_order_status", "warehouse", "completer", "maintenance_type",
                                       "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                                       "appraisal", "shop", "purchase_time", "ori_created_time", "ori_creator", "handle_time",
                                       "handler_name", "finish_time", "fee", "quantity",  "buyer_nick", "last_handle_time",
                                       "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                                       "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                                       "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                                       "goods_code", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                                       "charge_status", "charge_amount", "charge_memory"]

                if order.is_decrypted:
                    for field in order_fields_partial:
                        if str(row[field]) != 'nan':
                            setattr(order, field, row[field])
                else:
                    for field in order_fields_entire:
                        if str(row[field]) != 'nan':
                            setattr(order, field, row[field])

                if update_sign:
                    if order.ori_creator == '系统' and order.handler:
                        order.ori_creator = order.handler
                    order.warning_time = order.last_handle_time
                    order.sign = 0
                    order.cause = ''
                if new_order:
                    if re.match('^配件', row['goods_name']):
                        order.is_part = True
                try:
                    order.creator = request.user.username
                    order.save()
                    logging(order, user, LogOriMaintenance, '创建或更新')
                    report_dic["successful"] += 1
                except Exception as e:
                    report_dic['error'].append(f"{row['order_id']} 保存出错 {e}")
                    report_dic["false"] += 1
                    continue
                if new_order:
                    summary_date = order.ori_created_time.date()
                    _q_summary_order = MaintenanceSummary.objects.filter(summary_date=summary_date)
                    if _q_summary_order.exists():
                        summary_order = _q_summary_order[0]
                    else:
                        summary_order = MaintenanceSummary()
                        summary_order.summary_date = summary_date
                    if order.is_part:
                        summary_order.created_count_p += 1
                    else:
                        summary_order.created_count += 1
                    try:
                        summary_order.creator = request.user.username
                        summary_order.save()
                        logging(summary_order, user, LogMaintenanceSummary, f'{order.order_id}新建增加')
                    except Exception as e:
                        report_dic['error'].append(f"{row['order_id']} 保存统计出错 {e}")
                        report_dic["false"] += 1
                        continue
            if update_sign or new_order:
                except_func = self.__class__.except_function_dict.get(order.ori_order_status, None)
                if except_func:
                    getattr(order, except_func)()
                else:
                    report_dic["error"].append(f"{order.order_id} 原单状态错误，请修正后导入")
                    continue
                if except_func == 'handle_cancel':
                    summary_date = order.ori_created_time.date()
                    _q_summary_order = MaintenanceSummary.objects.filter(summary_date=summary_date)
                    if _q_summary_order.exists():
                        summary_order = _q_summary_order[0]
                    else:
                        continue
                    if order.is_part:
                        summary_order.created_count_p -= 1
                    else:
                        summary_order.created_count -= 1
                    try:
                        summary_order.creator = request.user.username
                        summary_order.save()
                        logging(summary_order, user, LogMaintenanceSummary, f"{order.order_id}取消减少")
                    except Exception as e:
                        report_dic['error'].append(f"{row['order_id']} 保存统计出错 {e}")
                        report_dic["false"] += 1
                        continue
                if order.process_tag != 0 or order.order_status == 0 or order.ori_order_status == '已完成':
                    order.save()
                    logging(order, user, LogOriMaintenance, "自动过滤，进行标记更新")

            if new_order and order.machine_sn != "unknown" and order.order_status == 1:
                end_time = order.ori_created_time - datetime.timedelta(days=1)
                start_time = order.ori_created_time - datetime.timedelta(days=31)
                _q_order_count = OriMaintenance.objects.filter(machine_sn=order.machine_sn, finish_time__lt=end_time, finish_time__gt=start_time, order_status__gt=0).count()
                if _q_order_count > 0:
                    order.is_repeated = True
                    order.save()
                    logging(order, user, LogOriMaintenance, "自动判定为返修单")
        return report_dic


class OriMaintenanceSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.filter(order_status=1, ori_order_status="已完成").order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        params["ori_order_status"] = "已完成"
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["ori_order_status"] = "已完成"
        if all_select_tag:
            handle_list = OriMaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriMaintenance.objects.filter(id__in=order_ids, order_status=1)
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
            "discard": 0,
            "error": []
        }
        warehouse_fields = ['苏州小狗维修仓', '北京维修仓']
        if n:
            for obj in check_list:
                if obj.warehouse not in warehouse_fields:
                    obj.order_status = 2
                    obj.mistake_tag = 0
                    obj.process_tag = 0
                    obj.save()
                    logging(obj, user, LogOriMaintenance, "无需递交")
                    continue
                if not obj.is_decrypted:
                    data["error"].append("%s未解密的单据不可递交" % obj.id)
                    n -= 1
                    obj.mistake_tag = 7
                    obj.save()
                    continue

                _q_repeat_order = Maintenance.objects.filter(ori_order=obj)
                if _q_repeat_order.exists():
                    order = _q_repeat_order[0]
                    if order.order_status in [0, 1]:
                        order.order_status = 1
                    else:
                        n -= 1
                        data['error'].append("%s 已递交过的单据不可重复递交" % obj.order_id)
                        obj.mistake_tag = 4
                        obj.save()
                        continue
                else:
                    order = Maintenance()

                _q_customer = Customer.objects.filter(name=obj.return_mobile)
                if _q_customer.exists():
                    order.customer = _q_customer[0]
                else:
                    order.customer = Customer.objects.create(**{"name": str(obj.return_mobile), "memo": "保修单递交创建"})
                    logging(order.customer, user, LogCustomer, "保修单递交创建")

                _q_shop = Shop.objects.filter(name=obj.shop)
                if _q_shop.exists():
                    order.shop = _q_shop[0]
                else:
                    data["error"].append("%sUT系统无此店铺" % obj.id)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue

                _q_warehouse = Warehouse.objects.filter(name=obj.warehouse)
                if _q_warehouse.exists():
                    order.warehouse = _q_warehouse[0]
                else:
                    data["error"].append("%sUT系统无此仓库" % obj.id)
                    n -= 1
                    obj.mistake_tag = 6
                    obj.save()
                    continue

                if obj.maintenance_type == "以旧换新":
                    n -= 1
                    data["false"] += 1
                    obj.mistake_tag = 8
                    obj.save()
                    continue

                _spilt_addr = PickOutAdress(obj.return_area)
                _rt_addr = _spilt_addr.pickout_addr()
                if not isinstance(_rt_addr, dict):
                    n -= 1
                    data['error'].append(f"{obj.order_id}寄回区域无法提取省市")
                    obj.mistake_tag = 9
                    obj.save()
                    continue
                order.province = _rt_addr["province"]
                order.city = _rt_addr["city"]

                order_fields = ["ori_order", "order_id", "maintenance_type", "fault_type", "machine_sn", "is_repeated",
                                "appraisal", "description", "buyer_nick", "return_name", "return_mobile", "goods",
                                "is_guarantee", "charge_status", "charge_amount", "charge_memory", "ori_creator",
                                "ori_created_time", "completer", "finish_time", "purchase_time", "memo"]
                for field in order_fields:
                    setattr(order, field, getattr(obj, field, None))
                _q_maintenance_count = OriMaintenance.objects.filter(machine_sn=obj.machine_sn, order_status=2)
                maintenance_count = _q_maintenance_count.count() + 1
                if not order.is_repeated:
                    order.process_tag = 2
                if not re.match('^99\d+', str(obj.return_mobile)):
                    order.add_labels = f"保修{maintenance_count}次"
                    if order.is_repeated:
                        repeated_count = _q_maintenance_count.filter(is_repeated=True).count() + 1
                        order.add_labels = f"{order.add_labels} 返修{repeated_count}次"
                try:
                    order.ori_order = obj
                    order.creator = request.user.username
                    order.save()
                    data["successful"] += 1
                    logging(order, user, LogMaintenance, "递交创建")
                except Exception as e:
                    n -= 1
                    data['error'].append(f"{obj.order_id} 保存出错：{e}")
                    obj.mistake_tag = 10
                    obj.save()
                    continue

                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogOriMaintenance, "递交完成")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def decrypt(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "discard": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.is_decrypted:
                    n -= 1
                    data['error'].append(f"{obj.order_id}已解密无需解密")
                    obj.is_decrypted = True
                    obj.save()
                    logging(obj, user, LogOriMaintenance, "执行解密成功")
                    continue
                _q_customer_info = re.findall('{.*}', str(obj.return_memory))
                if len(_q_customer_info) == 1:
                    customer_info = str(_q_customer_info[0])
                    customer_info = re.sub("[!$%&\'*+,./:：;<=>?，。?★、…【】《》？（）() “”‘’！[\\]^_`{|}~\s]+", "", customer_info)
                    _q_mobile = re.findall(r'\d{11}', customer_info)
                    if len(_q_mobile) == 1:
                        obj.return_mobile = _q_mobile[0]
                    else:
                        n -= 1
                        data['error'].append(f"{obj.order_id}备注格式错误，手机号码错误")
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                    _q_customer_other = re.split(r'\d{11}', customer_info)
                    if len(_q_customer_other) == 2:
                        if len(_q_customer_other[0]) > len(_q_customer_other[1]):
                            obj.return_name = _q_customer_other[1]
                            address = _q_customer_other[0]
                        else:
                            obj.return_name = _q_customer_other[0]
                            address = _q_customer_other[1]
                        if address:
                            _spilt_addr = PickOutAdress(address)
                            _rt_addr = _spilt_addr.pickout_addr()
                            if not isinstance(_rt_addr, dict):
                                obj.return_address = f"{obj.return_area}{address}"
                            else:
                                check_words = str(_rt_addr["city"].name)[:2]
                                if check_words in obj.return_area:
                                    obj.return_address = address
                                else:
                                    obj.return_address = f"{obj.return_area}{address}"
                        else:
                            n -= 1
                            data['error'].append(f"{obj.order_id}没有地址")
                            obj.mistake_tag = 3
                            obj.save()
                            continue


                    else:
                        n -= 1
                        data['error'].append(f"{obj.order_id}备注格式错误，存在多个手机号码")
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                else:
                    n -= 1
                    data['error'].append(f"{obj.order_id}备注格式错误，大括号格式错误")
                    obj.mistake_tag = 3
                    obj.save()
                    continue

                obj.is_decrypted = True
                obj.save()
                logging(obj, user, LogOriMaintenance, "执行解密成功")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def brute_force_attack(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "discard": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.mistake_tag == 0:
                    n -= 1
                    data['error'].append(f"{obj.order_id}未操作单据不可直接暴力解密")
                    continue
                if obj.is_decrypted:
                    n -= 1
                    data['error'].append(f"{obj.order_id}已解密无需解密")
                    obj.is_decrypted = True
                    obj.save()
                    logging(obj, user, LogOriMaintenance, "执行解密成功")
                    continue
                series_number = obj.id
                if series_number > 999999999:
                    series_number = str(series_number)[:9]
                else:
                    series_number = str(series_number)
                filler_number = 9 - len(series_number)
                filler = '0' * filler_number
                return_mobile = f"99{filler}{series_number}"
                _q_customer = Customer.objects.filter(name=return_mobile)
                if not _q_customer:
                    cs_serializer = CustomerLabelSerializer(data={"name": return_mobile})
                    valid = cs_serializer.is_valid()
                    if not valid:
                        n -= 1
                        data['error'].append(f"{obj.order_id}暴力破解失败，需要联系管理员处理！")
                        continue
                    cs_serializer.save()
                obj.return_mobile = return_mobile
                obj.return_name = return_mobile
                obj.return_address = "暴力覆写地址"
                obj.is_decrypted = True
                obj.save()
                logging(obj, user, LogOriMaintenance, "执行暴解成功")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def relate_goods(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        relate_list = self.get_handle_list(params)
        n = len(relate_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in relate_list:
                if obj.goods:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}已关联货品")
                    continue
                if obj.goods_name:
                    goods_name = re.findall('[A-Za-z0-9- ]+', str(obj.goods_name))
                    if goods_name:
                        name = str(goods_name[0]).strip()
                    else:
                        n -= 1
                        data["false"] += 1
                        data['error'].append(f"{obj.order_id}货品名称为空")
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                    _q_goods = Goods.objects.filter(name=name, goods_attribute=1)
                    if _q_goods.exists():
                        obj.goods = _q_goods[0]
                        obj.save()
                        logging(obj, user, LogOriMaintenance, f"关联货品{obj.goods.name}")
                    else:
                        n -= 1
                        data["false"] += 1
                        data['error'].append(f"{obj.order_id}货品名称无法提取到整机型号")
                        obj.mistake_tag = 2
                        obj.save()
                        continue

        else:
            raise serializers.ValidationError("没有可驳回的单据！")
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
            "保修单号": "order_id",
            "保修单状态": "order_status",
            "收发仓库": "warehouse",
            "处理登记人": "completer",
            "保修类型": "maintenance_type",
            "故障类型": "fault_type",
            "送修类型": "transport_type",
            "序列号": "machine_sn",
            "换新序列号": "new_machine_sn",
            "关联订单号": "send_order_id",
            "保修结束语": "appraisal",
            "关联店铺": "shop",
            "购买时间": "purchase_time",
            "创建时间": "ori_created_time",
            "创建人": "ori_creator",
            "审核时间": "handle_time",
            "审核人": "handler_name",
            "保修完成时间": "finish_time",
            "保修金额": "fee",
            "保修数量": "quantity",
            "最后修改时间": "last_handle_time",
            "客户网名": "buyer_nick",
            "寄件客户姓名": "sender_name",
            "寄件客户手机": "sender_mobile",
            "寄件客户省市县": "sender_area",
            "寄件客户地址": "sender_address",
            "收件物流公司": "send_logistics_company",
            "收件物流单号": "send_logistics_no",
            "收件备注": "send_memory",
            "寄回客户姓名": "return_name",
            "寄回客户手机": "return_mobile",
            "寄回省市区": "return_area",
            "寄回地址": "return_address",
            "寄件指定物流公司": "return_logistics_company",
            "寄件物流单号": "return_logistics_no",
            "寄件备注": "return_memory",
            "保修货品商家编码": "goods_code",
            "保修货品名称": "goods_name",
            "保修货品简称": "goods_abbreviation",
            "故障描述": "description",
            "是否在保修期内": "is_guarantee",
            "收费状态": "charge_status",
            "收费金额": "charge_amount",
            "收费说明": "charge_memory"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["保修单号", "保修单状态", "收发仓库", "处理登记人", "保修类型", "故障类型", "送修类型", "序列号",
                             "换新序列号", "关联订单号", "保修结束语", "关联店铺", "购买时间", "创建时间", "创建人", "审核时间",
                             "审核人", "保修完成时间", "保修金额", "保修数量", "最后修改时间", "客户网名", "寄件客户姓名",
                             "寄件客户手机", "寄件客户省市县", "寄件客户地址", "收件物流公司", "收件物流单号", "收件备注",
                             "寄回客户姓名", "寄回客户手机", "寄回省市区", "寄回地址", "寄件指定物流公司", "寄件物流单号",
                             "寄件备注", "保修货品商家编码", "保修货品名称", "保修货品简称", "故障描述", "是否在保修期内",
                             "收费状态", "收费金额", "收费说明"]

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
            _ret_verify_field = OriMaintenance.verify_mandatory(columns_key)
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
            _q_repeat_order = OriMaintenance.objects.filter(order_id=row["order_id"])
            if _q_repeat_order.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["order_id"])
                continue
            for keyword in ["purchase_time", "ori_created_time", "handle_time", "finish_time", "last_handle_time"]:
                if row[keyword] == "0000-00-00 00:00:00":
                    row[keyword] = None
            order = OriMaintenance()
            order_fields = ["order_id", "order_status", "warehouse", "completer", "maintenance_type",
                            "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                            "appraisal", "shop", "purchase_time", "ori_created_time", "ori_creator", "handle_time",
                            "handler_name", "finish_time", "fee", "quantity", "last_handle_time", "buyer_nick",
                            "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                            "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                            "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                            "goods_code", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                            "charge_status", "charge_amount", "charge_memory"]
            for field in order_fields:
                setattr(order, field, row[field])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["order_id"])
                report_dic["false"] += 1

        return report_dic


class OriMaintenanceViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceSerializer
    filter_class = OriMaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_orimaintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenance.objects.none()
        queryset = OriMaintenance.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriMaintenanceFilter(params)
        serializer = OriMaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = OriMaintenance.objects.filter(id=id)[0]
        ret = getlogs(instance, LogOriMaintenance)
        return Response(ret)


class MaintenanceJudgmentViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.filter(process_tag__in=[0, 1]).order_by("machine_sn")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["process_tag__in"] = '0, 1'
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["process_tag__in"] = '0, 1'
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def get_fault(self, request, *args, **kwargs):
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
                if obj.process_tag == 1:
                    n -= 1
                    data['error'].append("%s 已锁定过缺陷单，不可重复锁定" % obj.order_id)
                    continue
                if obj.machine_sn != "unknown" and obj.order_status == 1:
                    end_time = obj.ori_created_time - datetime.timedelta(days=1)
                    start_time = obj.ori_created_time - datetime.timedelta(days=31)
                    _q_order = Maintenance.objects.filter(machine_sn=obj.machine_sn,
                                                          finish_time__lt=end_time, finish_time__gt=start_time,
                                                          order_status__gt=0).order_by("-finish_time")
                    if _q_order.exists():
                        fault_order = _q_order[0]
                        fault_order.is_fault = True
                        fault_order.process_tag = 1
                        fault_order.save()
                        logging(fault_order, user, LogMaintenance, "缺陷标记")
                        pass
                    else:
                        n -= 1
                        data['error'].append("%s 未查询到缺陷单" % obj.order_id)
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                try:
                    obj.process_tag = 1
                    obj.save()
                    logging(obj, user, LogMaintenance, "完成缺陷锁定")
                except Exception as e:
                    data["error"].append("%s保修单保存出错: %s" % (obj.id, e))
                    n -= 1
                    obj.save()
                    continue
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
                if obj.is_repeated:
                    if obj.process_tag == 0:
                        data["error"].append("%s返修单据未锁定缺陷" % obj.id)
                        n -= 1
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                if obj.is_fault:
                    if obj.fault_cause == 0:
                        data["error"].append("%s缺陷单据未确认原因" % obj.id)
                        n -= 1
                        obj.mistake_tag = 3
                        obj.save()
                        continue
                if obj.is_repeated and not obj.is_fault:
                    summary_date = obj.ori_created_time.date()
                    _q_summary_order = MaintenanceSummary.objects.filter(summary_date=summary_date)
                    if _q_summary_order.exists():
                        summary_order = _q_summary_order[0]
                    else:
                        summary_order = MaintenanceSummary()
                        summary_order.summary_date = summary_date
                    summary_order.repeat_count += 1
                    try:
                        summary_order.creator = request.user.username
                        summary_order.save()
                        logging(summary_order, user, LogMaintenanceSummary, f'{obj.order_id}返修增加')
                    except Exception as e:
                        data['error'].append(f"{obj.order_id} 保存统计出错 {e}")
                        data["false"] += 1
                        obj.mistake_tag = 4
                        obj.save()
                        continue
                else:
                    summary_date = obj.finish_time.date()
                    _q_summary_order = MaintenanceSummary.objects.filter(summary_date=summary_date)
                    if _q_summary_order.exists():
                        summary_order = _q_summary_order[0]
                    else:
                        summary_order = MaintenanceSummary()
                        summary_order.summary_date = summary_date
                    summary_order.fault_count += 1
                    try:
                        summary_order.creator = request.user.username
                        summary_order.save()
                        logging(summary_order, user, LogMaintenanceSummary, f'{obj.order_id}返修增加')
                    except Exception as e:
                        data['error'].append(f"{obj.order_id} 保存统计出错 {e}")
                        data["false"] += 1
                        obj.mistake_tag = 4
                        obj.save()
                        continue
                obj.process_tag = 2
                obj.save()
                logging(obj, user, LogMaintenance, "判责流程处理完成")
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


class MaintenanceSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=1)
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
            if check_list.filter(process_tag__in=[0, 1]).exists():
                raise serializers.ValidationError({"error": "存在未处理的单据！"})

            for obj in check_list:
                summary_date = obj.finish_time.date()
                _q_summary_order = MaintenanceSummary.objects.filter(summary_date=summary_date)
                if _q_summary_order.exists():
                    summary_order = _q_summary_order[0]
                else:
                    summary_order = MaintenanceSummary()
                    summary_order.summary_date = summary_date
                if obj.is_part:
                    summary_order.finished_count_p += 1
                else:
                    summary_order.finished_count += 1
                try:
                    summary_order.creator = request.user.username
                    summary_order.save()
                    logging(summary_order, user, LogMaintenanceSummary, f'{obj.order_id}完成增加')
                except Exception as e:
                    data['error'].append(f"{obj.order_id} 保存统计出错 {e}")
                    data["false"] += 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                if re.match('^99', str(obj.return_mobile)):
                    obj.order_status = 3
                else:
                    obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogMaintenance, "完成统计")
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
                obj.ori_maintenance.towork_status = 1
                obj.ori_maintenance.save()
                obj.order_status = 0
                obj.save()
                data["successful"] += 1
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
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
            "通话ID": "call_id",
            "类型": "category",
            "开启服务时间": "start_time",
            "结束服务时间": "end_time",
            "服务时长": "total_duration",
            "通话时长": "call_duration",
            "排队时长": "queue_time",
            "振铃时长": "ring_time",
            "静音时长": "muted_duration",
            "静音次数": "muted_time",
            "主叫号码": "calling_num",
            "被叫号码": "called_num",
            "号码归属地": "attribution",
            "用户名": "nickname",
            "手机号码": "smartphone",
            "ivr语音导航": "ivr",
            "分流客服组": "group",
            "接待客服": "servicer",
            "重复咨询": "repeated_num",
            "接听状态": "answer_status",
            "挂机方": "on_hook",
            "满意度": "satisfaction",
            "服务录音": "call_recording",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "咨询备注": "remark",
            "问题解决状态": "problem_status",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "产品型号": "goods_type",
            "出厂序列号": "m_sn",
            "是否建配件工单": "is_order",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "收件人姓名": "receiver",
            "建单手机": "mobile",
            "省市区": "area",
            "详细地址": "address"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["通话ID", "类型", "开启服务时间", "结束服务时间", "服务时长", "通话时长", "排队时长",
                             "振铃时长", "静音时长", "静音次数", "主叫号码", "被叫号码", "号码归属地", "用户名",
                             "手机号码", "ivr语音导航", "分流客服组", "接待客服", "重复咨询", "接听状态", "挂机方",
                             "满意度", "服务录音", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "咨询备注", "问题解决状态", "购买日期", "购买店铺", "产品型号", "出厂序列号",
                             "是否建配件工单", "补寄原因", "配件信息", "损坏部位", "损坏描述", "收件人姓名",
                             "建单手机", "省市区", "详细地址"]

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
            _ret_verify_field = Maintenance.verify_mandatory(columns_key)
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
            _q_calllog = Maintenance.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = Maintenance()
            order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                            "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                            "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                            "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                            "call_recording", "primary_classification", "secondary_classification",
                            "three_level_classification", "four_level_classification", "five_level_classification",
                            "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn", "is_order",
                            "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                            "area", "address"]
            for field in order_fields:
                setattr(order, field, row[field])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1

        return report_dic


class MaintenanceSignLabelViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 2
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids)
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
            "tag_successful": 0,
            "error": []
        }
        label_category = LabelCategory.objects.filter(name="系统内置")[0]
        if n:
            for obj in check_list:
                if re.match('^99', str(obj.return_mobile)):
                    obj.order_status = 3
                    obj.save()
                    continue
                if obj.add_labels:
                    add_labels = str(obj.add_labels).split()
                    add_error_tag = 0
                    for label in add_labels:
                        _q_label = Label.objects.filter(name=str(label))
                        if _q_label.exists():
                            label_obj = _q_label[0]
                            if label_obj.is_cancel:
                                data["error"].append(f"必须先恢复标签 {str(label_obj.name)} 后再操作")
                                obj.mistake_tag = 5
                                add_error_tag = 1
                                break
                        else:
                            serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
                            code = serial_number
                            label_data = {
                                "name": label,
                                "group": "SVC",
                                "category": label_category,
                                "creator": user.username,
                                "memo": "维修单打标自动创建",
                                "code": code,
                            }
                            try:

                                label_obj = Label.objects.create(**label_data)
                                label_obj.code = "%s-%s" % (label_obj.group, label_obj.id)
                                label_obj.save()
                                logging(label_obj, user, LogLabel, "创建")
                            except Exception as e:
                                data["error"].append(f"创建标签 {str(label)} 失败")
                                obj.mistake_tag = 6
                                break

                        _q_check_add_label_order = QueryLabel(label_obj, obj.customer)
                        if not _q_check_add_label_order:
                            _created_result = CreateLabel(label_obj, obj.customer, user)
                            if not _created_result:
                                data["error"].append(f"{obj.customer.name} 创建标签 {str(label_obj.name)} 失败")
                                obj.mistake_tag = 6
                                add_error_tag = 1
                                break
                if add_error_tag:
                    n -= 1
                    obj.save()
                    continue
                obj.mistake_tag = 0
                obj.order_status = 4
                obj.save()
                logging(obj, user, LogMaintenance, "完成打标")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def sign_area(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "tag_successful": 0,
            "error": []
        }
        label_category = LabelCategory.objects.filter(name="系统内置")[0]
        if n:
            for obj in check_list:
                if re.match('^99', str(obj.return_mobile)):
                    obj.order_status = 3
                    obj.save()
                    continue
                if obj.province:
                    label = obj.province.name
                    _q_label = Label.objects.filter(name=str(label))
                    if _q_label.exists():
                        label_obj = _q_label[0]
                        if label_obj.is_cancel:
                            data["error"].append(f"必须先恢复标签 {str(label_obj.name)} 后再操作")
                            n -= 1
                            continue
                    else:
                        serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
                        code = serial_number
                        label_data = {
                            "name": label,
                            "group": "PPL",
                            "category": label_category,
                            "creator": user.username,
                            "memo": "维修单打标自动创建",
                            "code": code,
                        }
                        try:

                            label_obj = Label.objects.create(**label_data)
                            label_obj.code = "%s-%s" % (label_obj.group, label_obj.id)
                            label_obj.save()
                            logging(label_obj, user, LogLabel, "创建")
                        except Exception as e:
                            data["error"].append(f"创建标签 {str(label)} 失败")
                            n -= 1
                            continue

                    if str(label_obj.name) not in obj.add_labels:
                        obj.add_labels = f'{obj.add_labels} {label_obj.name}'
                        obj.save()
                        logging(obj, user, LogMaintenance, f"添加标签{label_obj.name}")
                else:
                    data["error"].append(f"单据省市区不全")
                    n -= 1
                    continue

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def sign_product(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "tag_successful": 0,
            "error": []
        }
        label_category = LabelCategory.objects.filter(name="系统内置")[0]
        if n:
            for obj in check_list:
                if re.match('^99', str(obj.return_mobile)):
                    obj.order_status = 3
                    obj.save()
                    continue

                year = str(obj.purchase_time.year)
                if not re.match("^20", year):
                    data["error"].append(f"{obj.id}购买时间错误，无法添加货品标签")
                    n -= 1
                    continue
                goods_name = str(obj.goods.name).replace(' ', '')
                label = f'{year}-{goods_name}'

                _q_label = Label.objects.filter(name=str(label))
                if _q_label.exists():
                    label_obj = _q_label[0]
                    if label_obj.is_cancel:
                        data["error"].append(f"必须先恢复标签 {str(label_obj.name)} 后再操作")
                        n -= 1
                        continue
                else:
                    serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
                    code = serial_number
                    label_data = {
                        "name": label,
                        "group": "PROD",
                        "category": label_category,
                        "creator": user.username,
                        "memo": "维修单打标自动创建",
                        "code": code,
                    }
                    try:
                        label_obj = Label.objects.create(**label_data)
                        label_obj.code = "%s-%s" % (label_obj.group, label_obj.id)
                        label_obj.save()
                        logging(label_obj, user, LogLabel, "创建")
                    except Exception as e:
                        data["error"].append(f"创建标签 {str(label_obj.name)} 失败")
                        n -= 1
                        continue

                if str(label_obj.name) not in obj.add_labels:
                    obj.add_labels = f'{obj.add_labels} {label_obj.name}'
                    obj.save()
                    logging(obj, user, LogMaintenance, f"添加标签{label_obj.name}")

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
                obj.ori_maintenance.towork_status = 1
                obj.ori_maintenance.save()
                obj.order_status = 0
                obj.save()
                data["successful"] += 1
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
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
            "通话ID": "call_id",
            "类型": "category",
            "开启服务时间": "start_time",
            "结束服务时间": "end_time",
            "服务时长": "total_duration",
            "通话时长": "call_duration",
            "排队时长": "queue_time",
            "振铃时长": "ring_time",
            "静音时长": "muted_duration",
            "静音次数": "muted_time",
            "主叫号码": "calling_num",
            "被叫号码": "called_num",
            "号码归属地": "attribution",
            "用户名": "nickname",
            "手机号码": "smartphone",
            "ivr语音导航": "ivr",
            "分流客服组": "group",
            "接待客服": "servicer",
            "重复咨询": "repeated_num",
            "接听状态": "answer_status",
            "挂机方": "on_hook",
            "满意度": "satisfaction",
            "服务录音": "call_recording",
            "一级分类": "primary_classification",
            "二级分类": "secondary_classification",
            "三级分类": "three_level_classification",
            "四级分类": "four_level_classification",
            "五级分类": "five_level_classification",
            "咨询备注": "remark",
            "问题解决状态": "problem_status",
            "购买日期": "purchase_time",
            "购买店铺": "shop",
            "产品型号": "goods_type",
            "出厂序列号": "m_sn",
            "是否建配件工单": "is_order",
            "补寄原因": "order_category",
            "配件信息": "goods_details",
            "损坏部位": "broken_part",
            "损坏描述": "description",
            "收件人姓名": "receiver",
            "建单手机": "mobile",
            "省市区": "area",
            "详细地址": "address"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["通话ID", "类型", "开启服务时间", "结束服务时间", "服务时长", "通话时长", "排队时长",
                             "振铃时长", "静音时长", "静音次数", "主叫号码", "被叫号码", "号码归属地", "用户名",
                             "手机号码", "ivr语音导航", "分流客服组", "接待客服", "重复咨询", "接听状态", "挂机方",
                             "满意度", "服务录音", "一级分类", "二级分类", "三级分类", "四级分类", "五级分类",
                             "咨询备注", "问题解决状态", "购买日期", "购买店铺", "产品型号", "出厂序列号",
                             "是否建配件工单", "补寄原因", "配件信息", "损坏部位", "损坏描述", "收件人姓名",
                             "建单手机", "省市区", "详细地址"]

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
            _ret_verify_field = Maintenance.verify_mandatory(columns_key)
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
            _q_calllog = Maintenance.objects.filter(call_id=row["call_id"])
            if _q_calllog.exists():
                report_dic["discard"] += 1
                report_dic["error"].append("%s提交重复" % row["call_id"])
                continue
            order = Maintenance()
            order_fields = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                            "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num",
                            "called_num", "attribution", "nickname", "smartphone", "ivr", "group",
                            "servicer", "repeated_num", "answer_status", "on_hook", "satisfaction",
                            "call_recording", "primary_classification", "secondary_classification",
                            "three_level_classification", "four_level_classification", "five_level_classification",
                            "remark", "problem_status", "purchase_time", "shop", "goods_type", "m_sn", "is_order",
                            "order_category", "goods_details", "broken_part", "description", "receiver", "mobile",
                            "area", "address"]
            for field in order_fields:
                setattr(order, field, row[field])

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["call_id"])
                report_dic["false"] += 1

        return report_dic


class MaintenanceViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSerializer
    filter_class = MaintenanceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return Maintenance.objects.none()
        queryset = Maintenance.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenanceFilter(params)
        serializer = MaintenanceSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = MaintenanceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Maintenance.objects.filter(id__in=order_ids, order_status=3)
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
            reject_list.update(order_status=2)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Maintenance.objects.filter(id=id)[0]
        ret = getlogs(instance, LogMaintenance)
        return Response(ret)


class MaintenanceSummaryViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceSummarySerializer
    filter_class = MaintenanceSummaryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return MaintenanceSummary.objects.none()
        queryset = MaintenanceSummary.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenanceSummaryFilter(params)
        serializer = MaintenanceSummarySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = MaintenanceSummaryFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MaintenanceSummary.objects.filter(id__in=order_ids)
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
                start_time = datetime.datetime.combine(obj.summary_date, datetime.datetime.min.time())
                end_time = start_time + datetime.timedelta(days=1)

                finish_data = Maintenance.objects.filter(finish_time__gt=start_time, finish_time__lt=end_time)
                created_data = Maintenance.objects.filter(ori_created_time__gt=start_time, ori_created_time__lt=end_time)

                obj.created_count_p = created_data.filter(is_part=True).count()
                obj.created_count = created_data.filter(is_part=False).count()
                obj.repeat_count = created_data.filter(is_repeated=True).count()

                obj.finished_count_p = finish_data.filter(is_part=True).count()
                obj.finished_count = finish_data.filter(is_part=False).count()
                obj.fault_count = finish_data.filter(is_fault=True).count()

                obj.save()
                logging(obj, user, LogMaintenanceSummary, "手工更新统计数据")
        else:
            raise serializers.ValidationError("没有可更新的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def ori_recount(self, request, *args, **kwargs):
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
                start_time = datetime.datetime.combine(obj.summary_date, datetime.datetime.min.time())
                end_time = start_time + datetime.timedelta(days=1)
                created_data = OriMaintenance.objects.filter(ori_created_time__gt=start_time, ori_created_time__lt=end_time, order_status__gt=0)
                obj.created_count_p = created_data.filter(is_part=True).count()
                obj.created_count = created_data.filter(is_part=False).count()
                obj.repeat_count = created_data.filter(is_repeated=True).count()

                obj.save()
                logging(obj, user, LogMaintenanceSummary, "手工更新统计数据")
        else:
            raise serializers.ValidationError("没有可更新的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = MaintenanceSummary.objects.filter(id=id)[0]
        ret = getlogs(instance, LogMaintenanceSummary)
        return Response(ret)


class OriMaintenanceGoodsSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceGoodsSerializer
    filter_class = OriMaintenanceGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenanceGoods.objects.none()
        queryset = OriMaintenanceGoods.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = OriMaintenanceGoodsFilter(params)
        serializer = OriMaintenanceGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriMaintenanceGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriMaintenanceGoods.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def decrypt(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "discard": 0,
            "error": []
        }
        if n:
            for obj in check_list:
                if obj.is_decrypted:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}已解密无需解密")
                    continue
                if all((obj.return_name, obj.return_mobile, obj.return_address)):
                    if not re.match('\d{11}', str(obj.return_mobile)):
                        n -= 1
                        data["false"] += 1
                        data['error'].append(f"{obj.order_id}手机格式错误无法解密")
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                else:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}信息缺失无法解密")
                    obj.mistake_tag = 2
                    obj.save()
                    continue
                _q_order = OriMaintenance.objects.filter(order_id=obj.order_id)
                if _q_order.exists():
                    order = _q_order[0]
                else:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}不存在对应的保修单")
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                if order.order_status == 0:
                    obj.order_status = 0
                    obj.save()
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}保修单已取消，配件自动取消")
                    logging(obj, user, LogMaintenanceGoods, "保修单已取消，配件自动取消")
                    continue
                if order.is_decrypted:
                    obj.is_decrypted = True
                    obj.save()
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}保修单已解密，直接跳过")
                    continue
                order.return_mobile = obj.return_mobile
                order.return_address = obj.return_address
                order.return_name = obj.return_name
                order.is_decrypted = True
                order.save()
                logging(order, user, LogOriMaintenance, "配件单推送解密成功")
                obj.is_decrypted = True
                obj.save()
                logging(obj, user, LogOriMaintenanceGoods, "执行解密成功")
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
                if not obj.is_decrypted:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}未推送解密不可审核")
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                _q_order = Maintenance.objects.filter(order_id=obj.order_id)
                if _q_order.exists():
                    order = _q_order[0]
                else:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}保修单未递交不可审核")
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                try:
                    goods_order = obj.maintenancegoods
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}已递交，不可重复递交")
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                except Exception as e:
                    goods_order = MaintenanceGoods()
                _q_part = Goods.objects.filter(goods_id=obj.part_code)
                if _q_part.exists():
                    part = _q_part[0]
                else:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}UT不存在此配件")
                    obj.mistake_tag = 7
                    obj.save()
                    continue
                goods_order.order = order
                goods_order.ori_order = obj
                goods_order.part = part
                goods_order.quantity = obj.quantity
                goods_order.finish_time = obj.finish_time
                goods_order.creator = user.username
                try:
                    goods_order.save()
                    logging(goods_order, user, LogMaintenanceGoods, "创建")
                except Exception as e:
                    n -= 1
                    data["false"] += 1
                    data['error'].append(f"{obj.order_id}创建保修货品失败")
                    obj.mistake_tag = 8
                    obj.save()
                    continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.save()
                logging(obj, user, LogOriMaintenanceGoods, "审核单据")
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def handle_repeated(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        handle_list = self.get_handle_list(params)
        n = len(handle_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in handle_list:
                if not obj.is_repeated:
                    n -= 1
                    data["false"] += 1
                    data["error"].append("非二次维修单据不需要标记")
                    continue
                obj.is_month_filter = True
                obj.save()
                logging(obj, user, LogOriMaintenance, "已标记二次维修")
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
            '保修单号': 'order_id',
            '保修配件商家编码': 'part_code',
            '保修配件货品名称': 'part_name',
            '配件数量': 'quantity',
            '配件备注': 'part_memo',
            '处理状态': 'handling_status',
            '保修处理内容': 'handling_content',
            '收发仓库': 'warehouse',
            '保修货品商家编码': 'goods_code',
            '保修货品货品名称': 'goods_name',
            '序列号': 'machine_sn',
            '发货订单编号': 'send_order_id',
            '购买时间': 'purchase_time',
            '保修完成时间': 'finish_time',
            '寄回客户姓名': 'return_name',
            '寄回客户手机': 'return_mobile',
            '寄回省市区': 'return_area',
            '寄回地址': 'return_address',
            '是否在保修期内': 'is_guarantee'
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ['保修单号', '保修配件商家编码', '保修配件货品名称', '配件数量', '配件备注', '处理状态', '保修处理内容',
                             '收发仓库', '保修货品商家编码', '保修货品货品名称', '序列号', '发货订单编号', '购买时间',
                             '保修完成时间', '寄回客户姓名', '寄回客户手机', '寄回省市区', '寄回地址', '是否在保修期内']

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append(f"必要字段{e}不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = OriMaintenanceGoods.verify_mandatory(columns_key)
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

    def save_resources(self, request, resource):
        user = request.user
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}

        for row in resource:
            if row["handling_status"] == '已取消':
                report_dic["false"] += 1
                report_dic['error'].append(f"{row['order_id']}的{row['part_name']}已取消")
                continue
            if not re.match("^BX", row['order_id']):
                report_dic["false"] += 1
                report_dic['error'].append(f"{row['order_id']} 单据内容错误")
                continue
            row["machine_sn"] = str(row["machine_sn"]).upper()
            if not re.match("[A-Z0-9]{16}|\d{8}", str(row["machine_sn"])):
                row["machine_sn"] = "unknown"
            _q_repeat_order = OriMaintenanceGoods.objects.filter(order_id=row["order_id"], part_code=row["part_code"])
            if _q_repeat_order.exists():
                report_dic["false"] += 1
                report_dic['error'].append(f"{row['order_id']}的{row['part_name']} 已导入")
                continue
            else:
                order = OriMaintenanceGoods()
            # 新版数据库不支持全是0的时间格式。需要处理为空值
            for keyword in ["purchase_time", "finish_time"]:
                if row[keyword] == "0000-00-00 00:00:00" or str(row[keyword]) == 'nan':
                    row[keyword] = None
            # 单据对象的解密标记决定由哪个更新列表进行更新。

            order_fields_entire = ['order_id', 'part_code', 'part_name', 'quantity', 'part_memo', 'handling_status',
                                   'handling_content', 'warehouse', 'goods_code', 'goods_name', 'machine_sn',
                                   'send_order_id', 'purchase_time', 'finish_time', 'return_name', 'return_mobile',
                                   'return_area', 'return_address', 'is_guarantee']

            for field in order_fields_entire:
                if str(row[field]) != 'nan':
                    setattr(order, field, row[field])
            try:
                order.creator = request.user.username
                order.save()
                logging(order, user, LogOriMaintenanceGoods, '创建或更新')
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append(f"{row['order_id']} 保存出错 {e}")
                report_dic["false"] += 1
                continue
        return report_dic


class OriMaintenanceGoodsViewset(viewsets.ModelViewSet):
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
    serializer_class = OriMaintenanceGoodsSerializer
    filter_class = OriMaintenanceGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return OriMaintenanceGoods.objects.none()
        queryset = OriMaintenanceGoods.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriMaintenanceGoodsFilter(params)
        serializer = OriMaintenanceGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = OriMaintenanceGoods.objects.filter(id=id)[0]
        ret = getlogs(instance, LogOriMaintenanceGoods)
        return Response(ret)


class MaintenanceGoodsSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceGoodsSerializer
    filter_class = MaintenanceGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return MaintenanceGoods.objects.none()
        queryset = MaintenanceGoods.objects.filter(order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        params["order_status"] = 1
        f = MaintenanceGoodsFilter(params)
        serializer = MaintenanceGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = MaintenanceGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MaintenanceGoods.objects.filter(id__in=order_ids, order_status=1)
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
                _q_summary_part = MaintenancePartSummary.objects.filter(summary_date=obj.finish_time.date(), part=obj.part)
                if _q_summary_part.exists():
                    summary_part = _q_summary_part[0]
                    summary_part.quantity += obj.quantity
                else:
                    summary_part = MaintenancePartSummary()
                    summary_part.summary_date = obj.finish_time.date()
                    summary_part.part = obj.part
                    summary_part.quantity = obj.quantity
                    summary_part.creator = user.username
                try:
                    summary_part.save()
                    logging(summary_part, user, LogMaintenancePartSummary, f"{obj.order.order_id}完成统计")
                except Exception as e:
                    data["error"].append("%s统计失败" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogMaintenanceGoods, "统计完成")
        else:
            raise serializers.ValidationError("没有可清除的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def handle_repeated(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        handle_list = self.get_handle_list(params)
        n = len(handle_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in handle_list:
                if not obj.is_repeated:
                    n -= 1
                    data["false"] += 1
                    data["error"].append("非二次维修单据不需要标记")
                    continue
                obj.is_month_filter = True
                obj.save()
                logging(obj, user, LogOriMaintenance, "已标记二次维修")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class MaintenanceGoodsViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenanceGoodsSerializer
    filter_class = MaintenanceGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return MaintenanceGoods.objects.none()
        queryset = MaintenanceGoods.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenanceGoodsFilter(params)
        serializer = MaintenanceGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = MaintenanceGoods.objects.filter(id=id)[0]
        ret = getlogs(instance, LogMaintenanceGoods)
        return Response(ret)


class MaintenancePartSummaryViewset(viewsets.ModelViewSet):
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
    serializer_class = MaintenancePartSummarySerializer
    filter_class = MaintenancePartSummaryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['service.view_maintenance']
    }

    def get_queryset(self):
        if not self.request:
            return MaintenancePartSummary.objects.none()
        queryset = MaintenancePartSummary.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = MaintenancePartSummaryFilter(params)
        serializer = MaintenancePartSummarySerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = MaintenancePartSummaryFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = MaintenancePartSummary.objects.filter(id__in=order_ids)
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
                current_data = Maintenance.objects.filter(finish_date=obj.finish_date)
                obj.repeat_found = current_data.filter(found_tag=True).count()
                obj.repeat_today = current_data.filter(repeat_tag__in=[1, 2, 3, 4]).count()
                obj.creator = request.user.username
                obj.save()
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

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = MaintenancePartSummary.objects.filter(id=id)[0]
        ret = getlogs(instance, LogMaintenancePartSummary)
        return Response(ret)


class ServiceOrderChartViewset(viewsets.ViewSet, mixins.ListModelMixin):
    permission_classes = (IsAuthenticated, )
    def list(self, request, *args, **kwargs):

        data = {
            "card1": {
                "cck": 2,
                "ccm": 3
            },
            "ppc": "ok"
        }
        a= 2
        b =3
        # user = request.user
        # params = request.data
        # params.pop("page", None)
        # all_select_tag = params.pop("allSelectTag", None)
        # if all_select_tag:
        #     handle_list = MaintenanceSummaryFilter(params).qs
        # else:
        #     order_ids = params.pop("ids", None)
        #     if order_ids:
        #         handle_list = MaintenanceSummary.objects.filter(id__in=order_ids)
        #     else:
        #         handle_list = []

        return response.Response(data)

