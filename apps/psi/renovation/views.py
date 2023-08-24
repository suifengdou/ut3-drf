import re, datetime
import math, copy
import pandas as pd
import numpy as np
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import RenovationSerializer, RenovationGoodsSerializer, RenovationdetailSerializer, ROFilesSerializer
from .filters import RenovationFilter, RenovationGoodsFilter, RenovationdetailFilter, ROFilesFilter
from .models import Renovation, RenovationGoods, Renovationdetail, LogRenovation, LogRenovationGoods, LogRenovationdetail, ROFiles
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.psi.inventory.models import IORelation
from apps.psi.inbound.models import InboundDetail, LogInboundDetail, Inbound, LogInbound
from apps.dfc.manualorder.models import ManualOrder, MOGoods
from apps.utils.logging.loggings import getlogs, logging
from apps.psi.outbound.models import Outbound, OutboundDetail, LogOutbound, LogOutboundDetail
from ut3.settings import EXPORT_TOPLIMIT
from apps.utils.oss.aliyunoss import AliyunOSS


class RenovationSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationSerializer
    filter_class = RenovationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovation.objects.none()
        user = self.request.user
        queryset = Renovation.objects.filter(order_status=1, creator=user.username).order_by("-id")
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
        f = RenovationFilter(params)
        serializer = RenovationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["creator"] = user.username
        if all_select_tag:
            handle_list = RenovationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Renovation.objects.filter(id__in=order_ids, order_status=1)
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
                if obj.process_tag not in [1, 9]:
                    data["error"].append("%s 未锁定单据不可审核" % obj.id)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                all_goods_details = obj.renovationgoods_set.all()
                if not all_goods_details.exists():
                    if obj.process_tag != 9:
                        data["error"].append("%s 非特殊无配件不可审核" % obj.id)
                        n -= 1
                        obj.mistake_tag = 1
                        obj.save()
                        continue
                _q_outbound = Outbound.objects.filter(verification=obj.code)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status > 1:
                        data["error"].append("%s 关联出库单错误，联系管理员" % obj.id)
                        n -= 1
                        obj.mistake_tag = 7
                        obj.save()
                        continue
                    else:
                        outbound.order_status = 1
                else:
                    outbound = Outbound()
                    suffix = str(datetime.datetime.now().date()).replace("-", "")
                    outbound.code = f"ODO{suffix}"
                outbound.warehouse = obj.warehouse
                outbound.verification = obj.code
                try:
                    outbound.creator = user.username
                    outbound.save()
                    outbound.code = f'{outbound.code}-{outbound.id}'
                    outbound.save()
                    logging(outbound, user, LogOutbound, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.id} 关联出库单创建错误：{e}")
                    n -= 1
                    obj.mistake_tag = 8
                    obj.save()
                    continue
                outbound.outbounddetail_set.all().delete()
                for goods in all_goods_details:
                    outbound_goods_dict = {
                        "order": outbound,
                        "goods": goods.goods,
                        "code": outbound.code,
                        "category": 1,
                        "warehouse": obj.warehouse,
                        "quantity": goods.quantity,
                        "price": goods.price,
                        "memo": goods.memo,
                    }
                    outbound_goods = OutboundDetail.objects.create(**outbound_goods_dict)
                    outbound_goods.code = f'{outbound_goods.code}-{outbound_goods.id}'
                    outbound_goods.save()
                    logging(outbound_goods, user, LogOutboundDetail, "创建")
                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.order_status = 2
                obj.save()
                logging(obj, user, LogRenovation, "提交")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_retread(self, request, *args, **kwargs):
        user = request.user
        params = request.data
        set_list = self.get_handle_list(params)
        n = len(set_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in set_list:
                if not obj.sn:
                    data["error"].append("%s 没有SN不可锁定" % obj.code)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if obj.process_tag == 1:
                    data["error"].append("%s 不可重复锁定" % obj.code)
                    n -= 1
                    obj.mistake_tag = 1
                    obj.save()
                    continue
                if obj.process_tag in [5, 9]:
                    obj.process_tag = 1
                    obj.save()
                    logging(obj, user, LogRenovation, "重新锁定翻新")
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.verification)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status == 0:
                        outbound.order_status = 1
                    else:
                        data["error"].append("%s 已关联出库单，联系管理员" % obj.code)
                        n -= 1
                        obj.mistake_tag = 2
                        obj.save()
                        continue
                else:
                    outbound = Outbound()

                d = datetime.datetime.now()
                d_day = str(d.date()).replace("-", "")

                outbound.code = f"ODO{d_day}"
                outbound.warehouse = obj.warehouse
                outbound.verification = obj.verification
                outbound.creator = user.username
                try:
                    outbound.save()
                    outbound.code = f"{outbound.code}-{outbound.id}"
                    outbound.save()
                    logging(outbound, user, LogOutbound, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.code}创建出库单出错:{e}")
                    n -= 1
                    obj.mistake_tag = 3
                    obj.save()
                    continue
                outbound.outbounddetail_set.all().delete()
                outbound_detail_dict = {
                    "order": outbound,
                    "goods": obj.goods,
                    "code": outbound.code,
                    "category": obj.order.category,
                    "warehouse": obj.warehouse,
                    "quantity": 1,
                    "creator": user.username,
                }
                try:
                    outbound_detail = OutboundDetail.objects.create(**outbound_detail_dict)
                    outbound_detail.code = f"{outbound_detail.code}-{outbound_detail.id}"
                    outbound_detail.save()
                    logging(outbound_detail, user, LogOutboundDetail, "创建")
                except Exception as e:
                    data["error"].append(f"{obj.code}创建出库单明细出错:{e}")
                    n -= 1
                    obj.mistake_tag = 4
                    obj.save()
                    continue
                obj.process_tag = 1
                obj.save()
                logging(obj, user, LogRenovation, "锁定翻新")

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(set_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        user = self.request.user
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
                    data["error"].append("%s 未锁定单据不可设置特殊标记" % obj.id)
                    n -= 1
                    obj.mistake_tag = 10
                    obj.save()
                    continue
                obj.process_tag = 9
                obj.save()
                logging(obj, user, LogRenovation, "设置特殊标记")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def get_all_goods(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        goods_detail = instance.renovationgoods_set.all()
        serializer = RenovationGoodsSerializer(goods_detail, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def set_all_goods(self, request, *args, **kwargs):
        user = request.user
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        goods_details = request.data.get("goods_details", None)
        instance = Renovation.objects.filter(id=id)[0]
        if not goods_details:
            instance.renovationgoods_set.all().delete()
            return Response({"success": "配件明细清理成功"})
        instance.renovationgoods_set.all().delete()
        logging(instance, user, LogRenovation, "重置配件列表")
        content = []
        for detail in goods_details:
            detail["goods"] = Goods.objects.filter(id=detail["goods"])[0]
            detail["order"] = instance
            detail["creator"] = user.username
            detail.pop("id", None)
            detail.pop("xh", None)
            order_goods = RenovationGoods.objects.create(**detail)
            logging(order_goods, user, LogRenovationGoods, "创建")
            content.append(f'{detail["goods"].name}x{detail["quantity"]}')
        logging(instance, user, LogRenovation, f"添加配件{content}")
        return Response({"": ""})

    @action(methods=['patch'], detail=False)
    def get_all_detail(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        goods_detail = instance.renovationdetail_set.all()
        serializer = RenovationdetailSerializer(goods_detail, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def set_all_detail(self, request, *args, **kwargs):
        user = request.user
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        goods_details = request.data.get("goods_details", None)
        instance = Renovation.objects.filter(id=id)[0]
        if not goods_details:
            raise serializers.ValidationError("未找到明细单据！")
        for detail in goods_details:
            detail["goods"] = Goods.objects.filter(id=detail["goods"])[0]
            detail["order"] = instance
            detail["creator"] = user.username
            detail.pop("xh", None)
            d_id = detail.pop("id", None)
            if not d_id:
                raise serializers.ValidationError("系统错误，联系管理员！")
            Renovationdetail.objects.filter(id=d_id).update(**detail)
        logging(instance, user, LogRenovation, f"设置损耗")
        return Response({"": ""})

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
                _q_goods = obj.renovationgoods_set.all()
                if _q_goods.exists():
                    data["error"].append("%s 存在配件出库明细不可以取消" % obj.code)
                    n -= 1
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                obj.order_status = 0
                obj.save()
                logging(obj, user, LogRenovation, "取消翻新单")
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
            work_order = Renovation.objects.filter(id=id)[0]
        else:
            data = {
                "error": "系统错误联系管理员，无法回传单据ID！"
            }
            return Response(data)
        if files:
            prefix = "ut3s1/psi/renovation"
            a_oss = AliyunOSS(prefix, files)
            file_urls = a_oss.upload()
            for obj in file_urls["urls"]:
                photo_order = ROFiles()
                photo_order.url = obj["url"]
                photo_order.name = obj["name"]
                photo_order.suffix = obj["suffix"]
                photo_order.workorder = work_order
                photo_order.creator = user.username
                photo_order.save()
                logging(work_order, user, LogRenovation, f"上传图片{photo_order.name}")
            data = {
                "sucessful": "上传文件成功 %s 个" % len(file_urls["urls"]),
                "error": file_urls["error"]
            }
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)


class RenovationCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationSerializer
    filter_class = RenovationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovation.objects.none()
        user = self.request.user
        queryset = Renovation.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["order_status"] = 2
        f = RenovationFilter(params)
        serializer = RenovationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = RenovationFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Renovation.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def odopart(self, request, *args, **kwargs):
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
                if obj.process_tag != 0:
                    data["error"].append("%s 已出库单据不可重复出库" % obj.id)
                    n -= 1
                    obj.mistake_tag = 11
                    obj.save()
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.code)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    if outbound.order_status > 1:
                        data["error"].append("%s 关联出库单错误，联系管理员" % obj.id)
                        n -= 1
                        obj.mistake_tag = 7
                        obj.save()
                        continue

                    all_goods = outbound.outbounddetail_set.all().filter(order_status=1)
                    if all_goods.exists():
                        error_sign = 0
                        for goods in all_goods:
                            _q_inbounddetail = InboundDetail.objects.filter(goods=goods.goods, warehouse=goods.warehouse, category=1)

                            odo_quantity = copy.copy(goods.quantity)
                            if odo_quantity <= 0:
                                data["error"].append("%s 出库数量错误" % odo_quantity)
                                n -= 1
                                obj.mistake_tag = 18
                                obj.save()
                                error_sign = 1
                                break
                            if _q_inbounddetail.exists():
                                balance = _q_inbounddetail.aggregate(Sum("valid_quantity"))["valid_quantity__sum"]
                                if balance < odo_quantity:
                                    data["error"].append("%s 缺货无法出库" % goods.goods.name)
                                    n -= 1
                                    obj.mistake_tag = 13
                                    obj.save()
                                    error_sign = 1
                                    break
                                for inbounddetail in _q_inbounddetail:
                                    if inbounddetail.valid_quantity > odo_quantity:
                                        inbounddetail.valid_quantity -= odo_quantity
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail, f"{goods.code}销减库存{goods.quantity}")

                                        goods.order_status = 2
                                        goods.save()
                                        logging(goods, user, LogOutboundDetail, f"关联入库明细{inbounddetail.code}")

                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail,
                                                                                         outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = odo_quantity
                                            io_relation.save()
                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": odo_quantity
                                            })
                                        break
                                    else:
                                        io_quantity = copy.copy(inbounddetail.valid_quantity)
                                        odo_quantity -= inbounddetail.valid_quantity
                                        inbounddetail.valid_quantity = 0
                                        inbounddetail.order_status = 4
                                        inbounddetail.is_complelted = True
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail, f"{goods.code}清账库存销减库存{goods.quantity}")

                                        _q_check_inbound_detail = inbounddetail.order.inbounddetail_set.filter(
                                            order_status=3)
                                        if not _q_check_inbound_detail.exists():
                                            inbounddetail.order.order_status = 4
                                            inbounddetail.order.save()
                                            logging(inbounddetail.order, user, LogInbound, "完结入库单")

                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail,
                                                                                         outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = io_quantity
                                            io_relation.save()
                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": io_quantity
                                            })
                                        if odo_quantity == 0:
                                            goods.order_status = 2
                                            goods.save()
                                            logging(goods, user, LogOutboundDetail,
                                                    f"关联入库明细{inbounddetail.code}并完结出库明细")
                                            _q_check_outbound_detail = goods.order.outbounddetail_set.filter(
                                                order_status=1)
                                            if not _q_check_outbound_detail.exists():
                                                goods.order.order_status = 2
                                                goods.order.save()
                                                logging(goods.order, user, LogOutbound, "完结出库单")
                                            break
                            else:
                                data["error"].append("%s 库存不存在" % goods.goods)
                                n -= 1
                                obj.mistake_tag = 12
                                obj.save()
                                error_sign = 1
                                break
                        if error_sign:
                            continue

                    outbound.order_status = 2
                    outbound.save()
                    logging(outbound, user, LogOutbound, "出库完成")
                obj.mistake_tag = 0
                obj.process_tag = 1
                obj.save()
                logging(obj, user, LogRenovation, "配件出库完成")
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def odobroken(self, request, *args, **kwargs):
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
                    data["error"].append("%s 出库单据未出库配件" % obj.id)
                    n -= 1
                    obj.mistake_tag = 14
                    obj.save()
                    continue
                _q_outbound = Outbound.objects.filter(verification=obj.verification, order_status=1)
                if _q_outbound.exists():
                    outbound = _q_outbound[0]
                    all_goods = outbound.outbounddetail_set.all().filter(order_status=1)
                    if all_goods.exists():
                        error_sign = 0
                        for goods in all_goods:
                            _q_inbounddetail = InboundDetail.objects.filter(goods=goods.goods, order__verification=obj.verification,
                                                                            warehouse=goods.warehouse, category=2)
                            odo_quantity = copy.copy(goods.quantity)
                            if odo_quantity <= 0:
                                data["error"].append("%s 出库数量错误" % odo_quantity)
                                n -= 1
                                obj.mistake_tag = 18
                                obj.save()
                                error_sign = 1
                                break
                            if _q_inbounddetail.exists():
                                balance = _q_inbounddetail.aggregate(Sum("valid_quantity"))["valid_quantity__sum"]
                                if balance < odo_quantity:
                                    data["error"].append("%s 缺货无法出库" % goods.goods.name)
                                    n -= 1
                                    obj.mistake_tag = 13
                                    obj.save()
                                    error_sign = 1
                                    break
                                for inbounddetail in _q_inbounddetail:
                                    if inbounddetail.valid_quantity > odo_quantity:
                                        inbounddetail.valid_quantity -= odo_quantity
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail,
                                                f"{goods.code}销减库存{goods.quantity}")

                                        goods.order_status = 2
                                        goods.save()
                                        logging(goods, user, LogOutboundDetail, f"关联入库明细{inbounddetail.code}")

                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail,
                                                                                         outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = odo_quantity
                                            io_relation.save()
                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": odo_quantity
                                            })
                                        break
                                    else:
                                        io_quantity = copy.copy(inbounddetail.valid_quantity)
                                        odo_quantity -= inbounddetail.valid_quantity
                                        inbounddetail.valid_quantity = 0
                                        inbounddetail.order_status = 4
                                        inbounddetail.is_complelted = True
                                        inbounddetail.save()
                                        logging(inbounddetail, user, LogInboundDetail,
                                                f"{goods.code}清账库存销减库存{goods.quantity}")

                                        _q_check_inbound_detail = inbounddetail.order.inbounddetail_set.filter(
                                            order_status=3)
                                        if not _q_check_inbound_detail.exists():
                                            inbounddetail.order.order_status = 4
                                            inbounddetail.order.save()
                                            logging(inbounddetail.order, user, LogInbound, "完结入库单")

                                        _q_check_io_relation = IORelation.objects.filter(inbound=inbounddetail,
                                                                                         outbound=goods)
                                        if _q_check_io_relation.exists():
                                            io_relation = _q_check_io_relation[0]
                                            io_relation.quantity = io_quantity
                                            io_relation.save()
                                        else:
                                            IORelation.objects.create(**{
                                                "inbound": inbounddetail,
                                                "outbound": goods,
                                                "category": goods.category,
                                                "quantity": io_quantity
                                            })
                                        if odo_quantity == 0:
                                            goods.order_status = 2
                                            goods.save()
                                            logging(goods, user, LogOutboundDetail,
                                                    f"关联入库明细{inbounddetail.code}并完结出库明细")
                                            _q_check_outbound_detail = goods.order.outbounddetail_set.filter(
                                                order_status=1)
                                            if not _q_check_outbound_detail.exists():
                                                goods.order.order_status = 2
                                                goods.order.save()
                                                logging(goods.order, user, LogOutbound, "完结出库单")
                                            break
                            else:
                                data["error"].append("%s 库存不存在" % goods.goods)
                                n -= 1
                                obj.mistake_tag = 12
                                obj.save()
                                error_sign = 1
                                break
                        if error_sign:
                            continue
                    outbound.order_status = 2
                    outbound.save()
                    logging(outbound, user, LogOutbound, "出库完成")

                obj.mistake_tag = 0
                obj.process_tag = 2
                obj.save()
                logging(obj, user, LogRenovation, "残品出库完成")
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
                if obj.process_tag != 2:
                    data["error"].append("%s 已出库单据未出库残品" % obj.id)
                    n -= 1
                    obj.mistake_tag = 15
                    obj.save()
                    continue
                _q_inbound = Inbound.objects.filter(verification=obj.code)
                if _q_inbound.exists():
                    data["error"].append("%s 已出库单据已存在正品入库单" % obj.id)
                    n -= 1
                    obj.mistake_tag = 16
                    obj.save()
                    continue
                suffix = str(datetime.datetime.now().date()).replace("-", "")
                inbound = Inbound.objects.create(**{
                    "code": f"DTS{suffix}",
                    "warehouse": obj.warehouse,
                    "verification": obj.verification,
                    "category": 4,
                    "memo": f"翻新入库单号：{obj.code}",
                    "creator": user.username
                })
                inbound.code = f"{inbound.code}-{inbound.id}"
                inbound.save()
                logging(inbound, user, LogInbound, "创建并完成")

                inbound_detail = InboundDetail.objects.create(**{
                    "order": inbound,
                    "goods": obj.goods,
                    "code": inbound.code,
                    "category": 1,
                    "warehouse": inbound.warehouse,
                    "quantity": 1,
                    "valid_quantity": 1,
                    "memo": f"翻新入库单号：{obj.code}",
                    "handle_time": datetime.datetime.now(),
                    "creator": user.username
                })
                inbound_detail.code = f"{inbound_detail.code}-{inbound_detail.id}"
                inbound_detail.save()
                logging(inbound_detail, user, LogInboundDetail, "创建并完成")



                inbound.order_status = 3
                inbound.save()
                inbound_detail.order_status = 3
                inbound_detail.save()

                obj.mistake_tag = 0
                obj.process_tag = 0
                obj.order_status = 3
                obj.save()
                logging(obj, user, LogRenovation, "审核完成正品入库成功")
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
                if obj.process_tag != 0:
                    data["error"].append("%s 已操作出库单据无法驳回" % obj.id)
                    n -= 1
                    obj.mistake_tag = 17
                    obj.save()
                    continue
                obj.order_status = 1
                obj.process_tag = 5
                obj.save()
                logging(obj, user, LogRenovation, "驳回翻新单")
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def get_all_goods(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        goods_detail = instance.renovationgoods_set.all()
        serializer = RenovationGoodsSerializer(goods_detail, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_all_detail(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        goods_detail = instance.renovationdetail_set.all()
        serializer = RenovationdetailSerializer(goods_detail, many=True)
        return Response(serializer.data)


class RenovationManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationSerializer
    filter_class = RenovationFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['renovation.view_renovation']
    }

    def get_queryset(self):
        if not self.request:
            return Renovation.objects.none()
        user = self.request.user
        queryset = Renovation.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationFilter(params)
        serializer = RenovationSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovation)
        return Response(ret)

    @action(methods=['patch'], detail=False)
    def get_file_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovation.objects.filter(id=id)[0]
        file_details = instance.rofiles_set.filter(is_delete=False)
        ret = []
        for file_detail in file_details:
            if file_detail.suffix in ['png', 'jpg', 'gif', 'bmp', 'tif', 'svg', 'raw']:
                is_pic = True
            else:
                is_pic = False
            data = {
                "id": file_detail.id,
                "name": file_detail.name,
                "suffix": file_detail.suffix,
                "url": file_detail.url,
                "url_list": [file_detail.url],
                "is_pic": is_pic
            }
            ret.append(data)
        return Response(ret)


class ROFilesManageViewset(viewsets.ModelViewSet):
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
    serializer_class = ROFilesSerializer
    filter_class = ROFilesFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return ROFiles.objects.none()
        user = self.request.user
        queryset = ROFiles.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = ROFilesFilter(params)
        serializer = ROFilesSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

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
            photo_order = ROFiles.objects.filter(id=id, creator=user.username, is_delete=False)
            if photo_order.exists():
                photo_order = photo_order[0]
                photo_order.is_delete = 1
                photo_order.save()
                data["successful"] += 1
                logging(photo_order.workorder, user, LogRenovation, f"删除图片{photo_order.name}")
            else:
                data["false"] += 1
                data["error"].append("只有创建者才有删除权限")
        else:
            data["false"] += 1
            data["error"].append("没有找到删除对象")
        return Response(data)


class RenovationGoodsManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationGoodsSerializer
    filter_class = RenovationGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return RenovationGoods.objects.none()
        user = self.request.user
        queryset = RenovationGoods.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationGoodsFilter(params)
        serializer = RenovationGoodsSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = RenovationGoods.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovationGoods)
        return Response(ret)


class RenovationdetailManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RenovationdetailSerializer
    filter_class = RenovationdetailFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['inbound.view_inbound']
    }

    def get_queryset(self):
        if not self.request:
            return Renovationdetail.objects.none()
        user = self.request.user
        queryset = Renovationdetail.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = RenovationdetailFilter(params)
        serializer = RenovationdetailSerializer(f.qs[:EXPORT_TOPLIMIT], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def get_log_details(self, request, *args, **kwargs):
        id = request.data.get("id", None)
        if not id:
            raise serializers.ValidationError("未找到单据！")
        instance = Renovationdetail.objects.filter(id=id)[0]
        ret = getlogs(instance, LogRenovationdetail)
        return Response(ret)

































