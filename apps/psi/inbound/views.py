import re, datetime
import math
import pandas as pd
import numpy as np
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import OriInboundSerializer, InboundSerializer, InboundDetailSerializer
from .filters import OriInboundFilter, InboundFilter, InboundDetailFilter
from .models import OriInbound, Inbound, InboundDetail, LogInbound, LogInboundDetail, LogOriInbound
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.psi.inventory.models import Inventory
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.utils.logging.loggings import getlogs, logging
from ut3.settings import EXPORT_TOPLIMIT


class OriInboundSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriInboundSerializer
    filter_class = OriInboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_oriinbound']
    }

    def get_queryset(self):
        if not self.request:
            return OriInbound.objects.none()
        user = self.request.user
        queryset = OriInbound.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = OriInboundFilter(params)
        serializer = OriInboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriInboundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriInbound.objects.filter(id__in=order_ids, order_status=1)
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
        category_list = {
            "采购入库": 1,
            "调拨入库": 2,
            "退货入库": 3,
            "生产入库": 4,
            "保修入库": 5,
            "其他入库": 6
        }
        if n:
            for obj in check_list:

                _q_goods = Goods.objects.filter(goods_id=obj.goods_id)
                if _q_goods.exists():
                    goods_name = _q_goods[0]
                else:
                    data["error"].append("%s 系统无此货品" % obj.order_id)
                    obj.mistake_tag = 3
                    obj.save()
                    n -= 1
                    continue
                _q_warehosue = Warehouse.objects.filter(name=obj.warehouse)
                if _q_warehosue.exists():
                    warehouse = _q_warehosue[0]
                else:
                    data["error"].append("%s 系统无此仓库" % obj.order_id)
                    obj.mistake_tag = 2
                    obj.save()
                    n -= 1
                    continue
                if not warehouse.order_status:
                    data["error"].append("%s 仓库设置监控" % obj.order_id)
                    obj.mistake_tag = 11
                    obj.save()
                    n -= 1
                    continue
                category = category_list.get(obj.category, None)
                if not category:
                    data["error"].append("%s 类别错误" % obj.order_id)
                    obj.mistake_tag = 4
                    obj.save()
                    n -= 1
                    continue
                _q_repeated_order = Inbound.objects.filter(order_id=obj.order_id)
                if _q_repeated_order.exists():
                    order = _q_repeated_order[0]
                    if order.order_status > 2:
                        data["error"].append("%s 此入库单号状态完成，不可递交" % obj.order_id)
                        obj.mistake_tag = 1
                        obj.save()
                        n -= 1
                        continue
                    elif order.order_status == 0:
                        order.order_status = 2
                        order.warehouse = warehouse
                        order.category = category
                    elif order.order_status == 2:
                        if order.warehouse != warehouse:
                            data["error"].append("%s 此入库单合并仓库不一致" % obj.order_id)
                            obj.mistake_tag = 5
                            obj.save()
                            n -= 1
                            continue
                        if order.category != category:
                            data["error"].append("%s 此入库单合并类别不一致" % obj.order_id)
                            obj.mistake_tag = 6
                            obj.save()
                            n -= 1
                            continue
                else:
                    order = Inbound()
                    order.order_id = obj.order_id
                    order.warehouse = warehouse
                    order.category = category

                try:
                    order.handle_time = datetime.datetime.now()
                    order.creator = request.user.username
                    order.order_status = 2
                    order.save()

                except Exception as e:
                    data["error"].append("%s 保存出错" % obj.order_id)
                    obj.mistake_tag = 8
                    obj.save()
                    n -= 1
                    continue
                _q_goods_detail = InboundDetail.objects.filter(ib_order_id=order, goods_name=goods_name)
                if _q_goods_detail.exists():
                    data["error"].append("%s 明细重复递交" % obj.order_id)
                    obj.mistake_tag = 9
                    obj.save()
                    n -= 1
                    continue
                else:
                    order_detail = InboundDetail()
                    order_detail.goods_name = goods_name
                    order_detail.goods_id = goods_name.goods_id
                    order_detail.quantity = obj.quantity
                    order_detail.ib_order_id = order
                    try:
                        order_detail.creator = request.user.username
                        order_detail.order_status = 2
                        order_detail.save()
                    except Exception as e:
                        data["error"].append("%s 明细保存出错" % obj.order_id)
                        obj.mistake_tag = 10
                        obj.save()
                        n -= 1
                        continue
                obj.handle_time = datetime.datetime.now()
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
            "入库单号": "order_id",
            "状态": "ori_order_status",
            "类别": "category",
            "源单号": "ori_order_id",
            "仓库": "warehouse",
            "经办人": "handler",
            "商家编码": "goods_id",
            "货品名称": "goods_name",
            "调整后数量": "quantity",
            "建单时间": "create_time",
            "审核入库时间": "handle_time",
            "备注": "memorandum"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["入库单号", "状态", "类别", "源单号", "仓库", "经办人", "商家编码", "货品名称",
                             "调整后数量", "建单时间", "审核入库时间", "备注"]

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
            _ret_verify_field = OriInbound.verify_mandatory(columns_key)
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
            order_fields = ["order_id", "ori_order_status", "category", "ori_order_id",
                            "warehouse", "handler", "goods_id", "goods_name", "quantity",
                            "create_time", "handle_time", "memorandum"]
            order = OriInbound()
            for field in order_fields:
                setattr(order, field, row[field])
            if len(str(order.memorandum)) > 150:
                order.memorandum = str(order.memorandum)[:150]
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["order_id"])
                report_dic["false"] += 1

        return report_dic


class OriInboundManageViewset(viewsets.ModelViewSet):
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
    serializer_class = OriInboundSerializer
    filter_class = OriInboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_oriinbound']
    }

    def get_queryset(self):
        if not self.request:
            return OriInbound.objects.none()
        user = self.request.user
        queryset = OriInbound.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = OriInboundFilter(params)
        serializer = OriInboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriInboundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriInbound.objects.filter(id__in=order_ids, order_status=1)
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
                _q_repeated_order = OriInbound.objects.filter(sent_consignee=obj.sent_consignee,
                                                                order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
                        obj.save()
                        n -= 1
                        continue
                _q_repeated_order = OriInbound.objects.filter(sent_smartphone=obj.sent_smartphone,
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


class InboundSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundSerializer
    filter_class = InboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Inbound.objects.none()
        user = self.request.user
        queryset = Inbound.objects.filter(order_status=1, creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        f = InboundFilter(params)
        serializer = InboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = InboundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Inbound.objects.filter(id__in=order_ids, order_status=1)
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
                all_goods_details = obj.inbounddetail_set.filter(order_status=1)
                if not all_goods_details.exists():
                    data["error"].append("%s 无货品不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                obj.order_status = 2
                for goods in all_goods_details:
                    goods.order_status = 2
                    goods.save()
                    logging(goods, user, LogInboundDetail, "提交")
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogInbound, "提交")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
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


class InboundCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundSerializer
    filter_class = InboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Inbound.objects.none()
        user = self.request.user
        queryset = Inbound.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = InboundFilter(params)
        serializer = InboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = InboundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Inbound.objects.filter(id__in=order_ids, order_status=2)
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
                all_goods_details = obj.inbounddetail_set.all()
                for goods_detail in all_goods_details:
                    goods_detail.valid_quantity = goods_detail.quantity
                    goods_detail.handle_time = datetime.datetime.now()
                    goods_detail.order_status = 3
                    goods_detail.save()
                    logging(goods_detail, user, LogInboundDetail, "入库成功")
                    _q_inventory = Inventory.objects.filter(warehouse=obj.warehouse, goods_name=goods_detail.goods)
                    if not _q_inventory.exists():
                        inventory_order = Inventory()
                        inventory_order.warehouse = obj.warehouse
                        inventory_order.goods_name = goods_detail.goods
                        inventory_order.goods_id = goods_detail.goods.goods_id
                        inventory_order.creator = user.username
                        inventory_order.save()

                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogInbound, "审核入库")
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


class InboundValidViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundSerializer
    filter_class = InboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Inbound.objects.none()
        user = self.request.user
        queryset = Inbound.objects.filter(order_status=3).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.query_params
        params["order_status"] = 3
        f = InboundFilter(params)
        serializer = InboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = InboundFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Inbound.objects.filter(id__in=order_ids, order_status=3)
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
                all_goods_details = obj.inbounddetail_set.all()
                for goods_detail in all_goods_details:
                    goods_detail.valid_quantity = goods_detail.quantity
                    goods_detail.handle_time = datetime.datetime.now()
                    goods_detail.order_status = 3
                    goods_detail.save()
                    logging(goods_detail, user, LogInboundDetail, "入库成功")
                    _q_inventory = Inventory.objects.filter(warehouse=obj.warehouse, goods_name=goods_detail.goods)
                    if not _q_inventory.exists():
                        inventory_order = Inventory()
                        inventory_order.warehouse = obj.warehouse
                        inventory_order.goods_name = goods_detail.goods
                        inventory_order.goods_id = goods_detail.goods.goods_id
                        inventory_order.creator = user.username
                        inventory_order.save()

                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.save()
                logging(obj, user, LogInbound, "审核入库")
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


class InboundManageViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundSerializer
    filter_class = InboundFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Inbound.objects.none()
        user = self.request.user
        queryset = Inbound.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = InboundFilter(params)
        serializer = InboundSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Inbound.objects.filter(id=id)[0]
        ret = getlogs(instance, LogInbound)
        return Response(ret)


class InboundDetailValidViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundDetailSerializer
    filter_class = InboundDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return InboundDetail.objects.none()
        user = self.request.user
        queryset = InboundDetail.objects.filter(order_status=3).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = InboundDetailFilter(params)
        serializer = InboundDetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 3
        if all_select_tag:
            handle_list = InboundDetailFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = InboundDetail.objects.filter(id__in=order_ids, order_status=3)
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
                pass
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


class InboundDetailManageViewset(viewsets.ModelViewSet):
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
    serializer_class = InboundDetailSerializer
    filter_class = InboundDetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return InboundDetail.objects.none()
        user = self.request.user
        queryset = InboundDetail.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = InboundDetailFilter(params)
        serializer = InboundDetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = InboundDetail.objects.filter(id=id)[0]
        ret = getlogs(instance, LogInboundDetail)
        return Response(ret)

































