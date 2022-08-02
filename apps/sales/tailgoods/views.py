import re, datetime
import math
import copy
import pandas as pd
import numpy as np
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import OriTailOrderSerializer, OTOGoodsSerializer, TailOrderSerializer, TOGoodsSerializer, \
    RefundOrderSerializer, ROGoodsSerializer, AccountInfoSerializer, TailToExpenseSerializer, \
    RefundToPrestoreSerializer
from .filters import OriTailOrderFilter, OTOGoodsFilter, TailOrderFilter, TOGoodsFilter, RefundOrderFilter, \
    ROGoodsFilter, AccountInfoFilter, TailToExpenseFilter, RefundToPrestoreFilter
from .models import OriTailOrder, OTOGoods, TailOrder, TOGoods, RefundOrder, ROGoods, AccountInfo, \
    TailToExpense, TailTOAccount, RefundToPrestore, ROGoodsToAccount
from apps.sales.advancepayment.models import Expense, Account, Statements, VerificationExpenses, ExpendList, Prestore
from apps.auth.users.models import UserProfile
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.sales.productcatalog.models import ProductCatalog


class OriTailOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = OriTailOrderSerializer
    filter_class = OriTailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_user_oritailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        user = self.request.user
        queryset = OriTailOrder.objects.filter(sign_company=user.company, order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["sign_company"] = user.company
        f = OriTailOrderFilter(params)
        serializer = OriTailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        user = self.request.user
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        params["sign_company"] = user.company
        if all_select_tag:
            handle_list = OriTailOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriTailOrder.objects.filter(id__in=order_ids, sign_company=user.company, order_status=1)
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
        all_prestores = account.prestore_set.filter(order_status=3)
        if all_prestores:
            balance = all_prestores.aggregate(Sum("remaining"))["remaining__sum"]
        else:
            raise serializers.ValidationError("账户无余额！")
        if not account.order_status:
            raise serializers.ValidationError("账户被冻结！")
        try:
            company = request.user.company
        except Exception as e:
            raise serializers.ValidationError("账号未关联公司！")
        if not company:
            raise serializers.ValidationError("账号未关联公司！")
        ori_await_amount = OriTailOrder.objects.filter(sign_company=company, order_status=2).aggregate(Sum("amount"))["amount__sum"]
        if not ori_await_amount:
            ori_await_amount = 0
        await_amount = TailOrder.objects.filter(sign_company=company, order_status=1).aggregate(Sum("amount"))["amount__sum"]
        if not await_amount:
            await_amount = 0
        submit_amount = check_list.aggregate(Sum("amount"))["amount__sum"]
        if not submit_amount:
            submit_amount = 0
        try:
            settlement_amount = (float(ori_await_amount) + float(submit_amount)) * float(company.discount_rate)
        except:
            raise serializers.ValidationError("关联公司未设置折扣！")
        settlement_amount = settlement_amount + await_amount
        if settlement_amount > balance:
            raise serializers.ValidationError("账户余额不足！")

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

                _q_repeated_order = OriTailOrder.objects.filter(sent_smartphone=obj.sent_smartphone,
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
                    check_name = check_name.lower()
                    contents = str(obj.message).lower()
                    if check_name not in contents:
                        data["error"].append("%s 发货型号与备注不符" % obj.order_id)
                        obj.mistake_tag = 16
                        obj.save()
                        n -= 1
                        continue
                user = request.user
                price_error = 0
                goods_details = obj.otogoods_set.all()
                for goods_detail in goods_details:
                    ori_goods = goods_detail.goods_name
                    ori_price = goods_detail.price
                    q_standard_price = ProductCatalog.objects.filter(goods=ori_goods, company=user.company, order_status=1)
                    if q_standard_price.exists():
                        standard_price = q_standard_price[0].price
                        if standard_price > ori_price:
                            price_error = 1
                            break
                    else:
                        price_error = 1
                        break
                if price_error:
                    data["error"].append("%s 发货型号未授权或金额错误" % obj.order_id)
                    obj.mistake_tag = 19
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


class OriTailOrderCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = OriTailOrderSerializer
    filter_class = OriTailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_oritailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        queryset = OriTailOrder.objects.filter(order_status=2).order_by("-id")
        return queryset

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = OriTailOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriTailOrder.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = OriTailOrderFilter(params)
        serializer = OriTailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

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
                if int(obj.quantity) > 1 and obj.process_tag != 6:
                    data["error"].append("%s 需要拆单的订单，用拆单递交，如发物流设置标记物流订单" % obj.order_id)
                    obj.mistake_tag = 5
                    obj.save()
                    n -= 1
                    continue

                _q_tail_order = TailOrder.objects.filter(ori_tail_order=obj)
                if _q_tail_order.exists():
                    _q_update_order = _q_tail_order.filter(order_status=0)
                    if _q_update_order.exists():
                        tail_order = _q_update_order[0]
                        tail_order.order_status = 1
                    else:
                        data["error"].append("%s 生成尾货订单重复，检查后处理" % obj.order_id)
                        obj.mistake_tag = 9
                        obj.save()
                        n -= 1
                        continue
                else:
                    tail_order = TailOrder()
                obj.handle_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(obj.submit_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(obj.handle_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                obj.handle_interval = math.floor(total_seconds / 60)
                copy_fields_order = ['shop', 'order_id', 'order_category', 'sent_consignee', 'sent_smartphone',
                                     'sent_city', 'sent_district', 'sent_address', 'amount', 'mode_warehouse',
                                     'message', 'creator', 'sign_company', 'sign_department']

                for key in copy_fields_order:
                    value = getattr(obj, key, None)
                    setattr(tail_order, key, value)

                tail_order.sent_province = obj.sent_city.province
                tail_order.ori_amount = obj.amount
                tail_order.quantity = obj.quantity
                tail_order.ori_tail_order = obj
                tail_order.submit_time = datetime.datetime.now()
                try:
                    tail_order.save()
                except Exception as e:
                    data["error"].append("%s 递交订单出错 %s" % (obj.order_id, e))
                    obj.mistake_tag = 6
                    obj.save()
                    n -= 1
                    continue
                _q_goods = obj.otogoods_set.all()
                amount = 0
                for good in _q_goods:
                    to_good = TOGoods()
                    to_good.tail_order = tail_order
                    to_good.goods_nickname = good.goods_name.name
                    copy_fields_goods = ['goods_id', 'goods_name', 'quantity', 'price', 'memorandum']
                    for key in copy_fields_goods:
                        value = getattr(good, key, None)
                        setattr(to_good, key, value)
                    try:
                        to_good.amount = to_good.quantity * to_good.price
                        to_good.settlement_price = round(to_good.price * obj.sign_company.discount_rate, 2)
                        to_good.settlement_amount = round(to_good.settlement_price * to_good.quantity, 2)
                        amount = round(to_good.settlement_amount + amount, 2)
                        to_good.creator = obj.creator
                        to_good.save()
                    except Exception as e:
                        data["error"].append("%s 生成订单货品出错 %s" % (obj.order_id, e))
                        obj.mistake_tag = 7
                        obj.save()
                        continue
                verify_tag = 0
                try:
                    expense_order = tail_order.tailtoexpense.expense
                    expense_order.order_status = 1
                except Exception as e:
                    expense_order = Expense()
                    verify_tag = 1
                    prefix = "EX"
                    serial_number = str(datetime.datetime.now())
                    serial_number = int(
                        serial_number.replace("-", "").replace(" ", "").replace(":", "").replace(".", ""))
                    expense_order.order_id = prefix + str(serial_number)[:18]
                user = UserProfile.objects.filter(username=tail_order.creator)[0]
                expense_order.account = Account.objects.filter(user=user)[0]
                expense_order.amount = amount
                expense_order.memorandum = "%s 店铺的 %s 销售订单 %s" % (str(tail_order.shop.name),
                                                                  str(tail_order.creator), str(tail_order.order_id))
                expense_order.creator = tail_order.creator
                try:
                    expense_order.save()
                except Exception as e:
                    data["error"].append("%s 生成支出单错误 %s" % (obj.order_id, e))
                    obj.mistake_tag = 18
                    obj.save()
                    tail_order.order_status = 0
                    tail_order.togoods_set.all().delete()
                    tail_order.save()
                    continue
                if verify_tag:
                    verify_order = TailToExpense()
                    verify_order.expense = expense_order
                    verify_order.tail_order = tail_order
                    verify_order.creator = obj.creator
                    verify_order.save()
                tail_order.amount = amount
                tail_order.save()
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 2
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def check_split(self, request, *args, **kwargs):
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
                if obj.mistake_tag == 5:
                    _q_goods = obj.otogoods_set.all()

                    l_name, l_quantity, l_price = [goods.goods_name for goods in _q_goods], [goods.quantity for goods in
                                                                                             _q_goods], [goods.price for
                                                                                                         goods in
                                                                                                         _q_goods]
                    groups = []
                    for i in range(len(l_name)):
                        if int(l_quantity[i]) == 1:
                            group = {l_name[i]: l_price[i]}
                            groups.append(group)
                        elif int(l_quantity[i]) > 1:
                            for j in range(int(l_quantity[i])):
                                group = {l_name[i]: l_price[i]}
                                groups.append(group)
                        else:
                            data["error"].append("%s 货品数量错误" % obj.order_id)
                            obj.mistake_tag = 8
                            obj.save()
                            n -= 1
                            continue

                    tail_quantity = len(groups)
                    for tail_num in range(tail_quantity):
                        tail_order = TailOrder()
                        series_number = tail_num + 1
                        order_id = '%s-%s' % (obj.order_id, series_number)

                        _q_tail_order = TailOrder.objects.filter(order_id=order_id)
                        if _q_tail_order.exists():
                            _q_update_order = _q_tail_order.filter(order_status=0)
                            if _q_update_order.exists():
                                tail_order = _q_update_order[0]
                                tail_order.order_status = 1
                            else:
                                data["error"].append("%s 生成尾货订单重复，检查后处理" % obj.order_id)
                                obj.mistake_tag = 9
                                obj.save()
                                n -= 1
                                continue
                        tail_order.order_id = order_id
                        tail_order.submit_time = datetime.datetime.now()
                        tail_order.ori_tail_order = obj
                        copy_fields_order = ['shop', 'order_category', 'sent_consignee', 'sent_smartphone',
                                             'sent_city', 'sent_district', 'sent_address', 'mode_warehouse',
                                             'message', 'sign_company', 'sign_department', 'creator']
                        for key in copy_fields_order:
                            value = getattr(obj, key, None)
                            setattr(tail_order, key, value)

                        tail_order.sent_province = obj.sent_city.province
                        tail_order.ori_amount = obj.amount
                        try:
                            tail_order.save()
                        except Exception as e:
                            data["error"].append("%s 生成订单出错，请仔细检查 %s" % (obj.order_id, e))
                            obj.mistake_tag = 10
                            obj.save()
                            n -= 1
                            continue
                        current_amount = 0
                        for goods, price in groups[tail_num].items():
                            goods_order = TOGoods()
                            goods_order.tail_order = tail_order
                            goods_order.goods_name = goods
                            goods_order.goods_nickname = goods.name
                            goods_order.goods_id = goods.goods_id
                            goods_order.quantity = 1
                            goods_order.price = price
                            goods_order.amount = price
                            goods_order.settlement_price = round(price * obj.sign_company.discount_rate, 2)
                            goods_order.settlement_amount = round(price * obj.sign_company.discount_rate, 2)
                            current_amount = goods_order.settlement_amount
                            goods_order.memorandum = '来源 %s 的第 %s 个订单' % (obj.order_id, tail_num + 1)

                            try:
                                goods_order.creator = obj.creator
                                goods_order.save()
                            except Exception as e:
                                data["error"].append("%s 生成订单货品出错，请仔细检查 %s" % (obj.order_id, e))
                                obj.mistake_tag = 11
                                obj.save()
                                n -= 1
                                continue

                        verify_tag = 0
                        try:
                            expense_order = tail_order.tailtoexpense.expense
                            expense_order.order_status = 1
                        except Exception as e:
                            expense_order = Expense()
                            verify_tag = 1
                            prefix = "EX"
                            serial_number = str(datetime.datetime.now())
                            serial_number = int(
                                serial_number.replace("-", "").replace(" ", "").replace(":", "").replace(".", ""))
                            expense_order.order_id = prefix + str(serial_number)[:18]
                        user = UserProfile.objects.filter(username=tail_order.creator)[0]
                        expense_order.account = Account.objects.filter(user=user)[0]
                        expense_order.amount = current_amount
                        expense_order.memorandum = "%s 店铺的 %s 销售订单 %s" % (str(tail_order.shop.name),
                                                                          str(tail_order.creator),
                                                                          str(tail_order.order_id))
                        expense_order.creator = tail_order.creator
                        try:
                            expense_order.save()
                        except Exception as e:
                            data["error"].append("%s 生成支出单错误 %s" % (obj.order_id, e))
                            obj.mistake_tag = 18
                            obj.save()
                            tail_order.order_status = 0
                            tail_order.togoods_set.all().delete()
                            tail_order.save()
                            continue
                        if verify_tag:
                            verify_order = TailToExpense()
                            verify_order.expense = expense_order
                            verify_order.tail_order = tail_order
                            verify_order.creator = obj.creator
                            verify_order.save()

                        tail_order.amount = current_amount
                        tail_order.quantity = 1
                        tail_order.save()

                    obj.handle_time = datetime.datetime.now()
                    start_time = datetime.datetime.strptime(str(obj.submit_time).split(".")[0],
                                                            "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.datetime.strptime(str(obj.handle_time).split(".")[0],
                                                          "%Y-%m-%d %H:%M:%S")
                    d_value = end_time - start_time
                    days_seconds = d_value.days * 3600
                    total_seconds = days_seconds + d_value.seconds
                    obj.handle_interval = math.floor(total_seconds / 60)
                    obj.order_status = 3
                    obj.mistake_tag = 0
                    obj.process_tag = 6
                    obj.save()

                else:
                    data["error"].append("%s 为标记拆分订单，请先用普通模式审核。" % obj.order_id)
                    obj.mistake_tag = 0
                    obj.save()
                    n -= 1
                    continue
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_logistics(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=6)
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
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class OriTailOrderViewset(viewsets.ModelViewSet):
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
    serializer_class = OriTailOrderSerializer
    filter_class = OriTailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_oritailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = OriTailOrder.objects.all().order_by("-id")
        else:
            queryset = OriTailOrder.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = OriTailOrderFilter(params)
        serializer = OriTailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


class OTOGoodsViewset(viewsets.ModelViewSet):
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
    serializer_class = OTOGoodsSerializer
    filter_class = OTOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_oritailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return OTOGoods.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = OTOGoods.objects.all().order_by("-id")
        else:
            queryset = OTOGoods.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = OTOGoodsFilter(params)
        serializer = OTOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)


class TailOrderCommonViewset(viewsets.ModelViewSet):
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
    serializer_class = TailOrderSerializer
    filter_class = TailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_user_tailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        queryset = TailOrder.objects.filter(mode_warehouse=1, order_status=1).order_by("-id")
        return queryset

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = TailOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = TailOrder.objects.filter(id__in=order_ids, order_status=1, mode_warehouse=1)
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
                if not obj.track_no:
                    data["error"].append("%s 物流追踪信息错误" % obj.order_id)
                    obj.mistake_tag = 1
                    obj.save()
                    n -= 1
                    continue
                if int(len(obj.track_no)) < 7:
                    data["error"].append("%s 物流追踪信息错误" % obj.order_id)
                    obj.mistake_tag = 1
                    obj.save()
                    n -= 1
                    continue

                if obj.process_tag != 4:
                    data["error"].append("%s 货品明细未发货，不可以审核" % obj.order_id)
                    obj.mistake_tag = 3
                    obj.save()
                    n -= 1
                    continue

                i = 1
                repeat_tag = 0
                goods_orders = obj.togoods_set.all()
                for goods_order in goods_orders:
                    _q_t2a = TailTOAccount.objects.filter(tail_goods=goods_order)
                    if _q_t2a:
                        data["error"].append("%s 生成尾货对账单重复，联系管理员处理" % obj.order_id)
                        obj.mistake_tag = 8
                        obj.save()
                        repeat_tag = 1
                        break

                    acc_order = AccountInfo()
                    copy_fields_order = ['shop', 'order_category', 'mode_warehouse', 'sent_consignee',
                                         'sign_company', 'sign_department', 'sent_smartphone', 'message']

                    for key in copy_fields_order:
                        value = getattr(obj, key, None)
                        setattr(acc_order, key, value)

                    copy_fields_goods = ['goods_id', 'goods_name', 'goods_nickname', 'quantity',
                                         'settlement_price', 'settlement_amount']

                    for key in copy_fields_goods:
                        value = getattr(goods_order, key, None)
                        setattr(acc_order, key, value)

                    acc_order.creator = self.request.user.username
                    acc_order.order_id = "%s-%s-%s" % (obj.order_id, i, goods_order.goods_id)
                    i += 1
                    acc_order.submit_time = datetime.datetime.now()
                    pb2acc_order = TailTOAccount()
                    pb2acc_order.tail_goods = goods_order
                    try:
                        acc_order.save()
                        pb2acc_order.account_order = acc_order
                        pb2acc_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成结算单出错 %s" % (obj.order_id, e))
                        obj.mistake_tag = 2
                        obj.save()
                        repeat_tag = 1
                        break
                if repeat_tag:
                    n -= 1
                    continue
                expense_order = obj.tailtoexpense.expense
                statement = Statements()
                _q_verifyexpense = VerificationExpenses.objects.filter(expense=expense_order)
                if _q_verifyexpense:
                    data["error"].append("%s 支出流水创建重复，联系管理员处理" % obj.order_id)
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                statement.order_id = "S" + expense_order.order_id
                statement.account = expense_order.account
                statement.category = expense_order.category
                statement.expenses = expense_order.amount
                statement.creator = obj.creator
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
                verifyexpense.creator = obj.creator
                try:
                    statement.save()
                    verifyexpense.statement = statement
                    verifyexpense.save()
                except Exception as e:
                    data["error"].append("%s 支出流水单错误 %s" % (obj.order_id, e))
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                all_prestores = Prestore.objects.filter(account=expense_order.account, order_status=3)
                charge_amount = expense_order.amount
                error_tag = 0
                for prestore in all_prestores:
                    if prestore.remaining > charge_amount:
                        prestore.remaining = round(prestore.remaining - charge_amount, 2)
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = round(charge_amount - prestore.remaining, 2)
                        actual_amount = prestore.remaining
                        prestore.remaining = 0
                        prestore.order_status = 4
                    expendlist = ExpendList()
                    expendlist.statements = statement
                    expendlist.account = expense_order.account
                    expendlist.prestore = prestore
                    expendlist.amount = actual_amount
                    expendlist.creator = obj.creator
                    try:
                        prestore.save()
                        expendlist.save()
                    except Exception as e:
                        data["error"].append("%s 支出划账错误 %s" % (obj.order_id, e))
                        obj.mistake_tag = 7
                        obj.save()
                        error_tag = 1
                        break
                    if charge_amount == 0:
                        break
                if error_tag:
                    continue
                expense_order.order_status = 2
                expense_order.save()
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 4

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
                if obj.mistake_tag in [0, 1]:
                    data["error"].append("%s 非异常状态订单不可修复" % obj.order_id)
                    continue
                i = 1
                goods_orders = obj.togoods_set.all()
                for goods_order in goods_orders:
                    _q_t2a = TailTOAccount.objects.filter(tail_goods=goods_order)
                    if _q_t2a:
                        acc_order = _q_t2a[0].account_order
                    else:
                        acc_order = AccountInfo()
                    copy_fields_order = ['shop', 'order_category', 'mode_warehouse', 'sent_consignee',
                                         'sign_company', 'sign_department', 'sent_smartphone', 'message']

                    for key in copy_fields_order:
                        value = getattr(obj, key, None)
                        setattr(acc_order, key, value)

                    copy_fields_goods = ['goods_id', 'goods_name', 'goods_nickname', 'quantity',
                                         'settlement_price', 'settlement_amount']

                    for key in copy_fields_goods:
                        value = getattr(goods_order, key, None)
                        setattr(acc_order, key, value)

                    acc_order.creator = obj.creator
                    if not acc_order.order_id:
                        acc_order.order_id = "%s-%s-%s" % (obj.order_id, i, goods_order.goods_id)
                    i += 1
                    acc_order.submit_time = datetime.datetime.now()
                    pb2acc_order = TailTOAccount()
                    pb2acc_order.tail_goods = goods_order
                    try:
                        acc_order.save()
                        pb2acc_order.account_order = acc_order
                        pb2acc_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成对账单出错 %s" % (obj.order_id, e))
                        obj.mistake_tag = 2
                        obj.save()
                        break
                expense_order = obj.tailtoexpense.expense
                _q_verifyexpense = VerificationExpenses.objects.filter(expense=expense_order)
                if _q_verifyexpense:
                    statement = _q_verifyexpense[0].statement
                else:
                    statement = Statements()
                if not statement.order_id:
                    statement.order_id = "S" + expense_order.order_id
                statement.account = expense_order.account
                statement.category = expense_order.category
                statement.expenses = expense_order.amount
                statement.creator = obj.creator
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
                verifyexpense.creator = obj.creator
                try:
                    statement.save()
                    verifyexpense.statement = statement
                    verifyexpense.save()
                except Exception as e:
                    data["error"].append("%s 支出流水单错误 %s" % (obj.order_id, e))
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                try:
                    charged_amount = ExpendList.objects.filter(Statements=statement).aggregate(Sum("amount"))["amount__sum"]
                except Exception as e:
                    charged_amount = 0
                if not charged_amount:
                    charged_amount = 0
                all_prestores = Prestore.objects.filter(account=expense_order.account, order_status=3)
                charge_amount = round(expense_order.amount - charged_amount, 2)
                error_tag = 0
                for prestore in all_prestores:
                    if prestore.remaining > charge_amount:
                        prestore.remaining = round(prestore.remaining - charge_amount, 2)
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = round(charge_amount - prestore.remaining, 2)
                        prestore.remaining = 0
                        prestore.order_status = 4
                        actual_amount = prestore.remaining
                    expendlist = ExpendList()
                    expendlist.statements = statement
                    expendlist.account = expense_order.account
                    expendlist.prestore = prestore
                    expendlist.amount = actual_amount
                    expendlist.creator = obj.creator
                    try:
                        expendlist.save()
                        prestore.save()
                    except Exception as e:
                        data["error"].append("%s 支出划账错误 %s" % (obj.order_id, e))
                        obj.mistake_tag = 7
                        obj.save()
                        error_tag = 1
                        break
                    if charge_amount == 0:
                        break
                if error_tag:
                    continue
                expense_order.order_status = 2
                expense_order.save()
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 4

                obj.save()

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                params["sign_department"] = user.department
            else:
                params["creator"] = user.username
        f = TailOrderFilter(params)
        serializer = TailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


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
                if obj.process_tag == 4:
                    data["error"].append("%s 存在已经标记发货的明细，不可以驳回！" % obj.order_id)
                    n -= 1
                    continue
                if obj.order_status > 0:
                    obj.order_status -= 1
                    obj.process_tag = 5
                    obj.save()
                    if obj.order_status == 0:
                        obj.togoods_set.all().delete()
                        _q_tail_orders = obj.ori_tail_order.tailorder_set.all().filter(order_status__in=[1, 2, 3])
                        if _q_tail_orders.exists():
                            data["error"].append("%s 取消成功，但是还存在其他子订单未驳回，源订单无法被驳回" % obj.order_id)
                            obj.ori_tail_order.process_tag = 7
                            obj.ori_tail_order.save()
                        else:
                            obj.ori_tail_order.order_status = 2
                            obj.ori_tail_order.process_tag = 5

                            obj.ori_tail_order.save()
                        expense = obj.tailtoexpense.expense
                        expense.order_status = 0
                        expense.save()
                    else:
                        data["error"].append("%s 驳回上一级成功" % obj.order_id)

                else:
                    n -= 1
                    data["error"].append("%s 单据状态错误，请检查，驳回出错。" % obj.order_id)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {"原始单号": "order_id", "物流单号": "track_no"}
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0)
                FILTER_FIELDS = ['原始单号', '物流单号']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    columns_key[i] = columns_key[i].replace(' ', '').replace('=', '')

                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = TailOrder.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic["error"].append(str(_ret_verify_field))
                    return report_dic

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
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                    i += 1
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        for order in resource:
            try:
                TailOrder.objects.filter(order_id=order["order_id"], order_status=1, mode_warehouse=1).update(track_no=order["track_no"])
                report_dic["successful"] += 1
            except Exception as e:
                report_dic["false"] += 1
                report_dic["error"].append(e)
        return report_dic


class TOGoodsCommonViewset(viewsets.ModelViewSet):
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
    serializer_class = TOGoodsSerializer
    filter_class = TOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_user_togoods',]
    }

    def get_queryset(self):
        if not self.request:
            return TOGoods.objects.none()
        queryset = TOGoods.objects.filter(is_delete=0, tail_order__order_status=1, tail_order__mode_warehouse=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["process_tag"] = 0
        params["tail_order__mode_warehouse"] = 1
        params["tail_order__order_status"] = 1

        f = TOGoodsFilter(params)
        serializer = TOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = TOGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = TOGoods.objects.filter(id__in=order_ids)
            else:
                handle_list = []
        return handle_list

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
            check_list.update(process_tag=4)
            for goods_order in check_list:
                _q_status = goods_order.tail_order.togoods_set.all().filter(process_tag=0)
                if _q_status.exists():
                    goods_order.tail_order.process_tag = 3
                else:
                    goods_order.tail_order.process_tag = 4
                goods_order.tail_order.save()
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
            for goods_order in check_list:
                goods_order.tail_order.process_tag = 0
                goods_order.tail_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)


class TailOrderSpecialViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定尾货单
    list:
        返回尾货单列表
    update:
        更新尾货单信息
    partial_update:
        更新部分公司字段
    """
    serializer_class = TailOrderSerializer
    filter_class = TailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_tailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        queryset = TailOrder.objects.filter(mode_warehouse=0, order_status=1).order_by("-id")
        return queryset


    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = TailOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = TailOrder.objects.filter(id__in=order_ids, order_status=1, mode_warehouse=0)
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
                if not obj.track_no:
                    data["error"].append("%s 物流追踪信息错误" % obj.order_id)
                    obj.mistake_tag = 1
                    obj.save()
                    n -= 1
                    continue
                if int(len(obj.track_no)) < 7:
                    data["error"].append("%s 物流追踪信息错误" % obj.order_id)
                    obj.mistake_tag = 1
                    obj.save()
                    n -= 1
                    continue

                if obj.process_tag != 4:
                    data["error"].append("%s 货品明细未发货，不可以审核" % obj.order_id)
                    obj.mistake_tag = 3
                    obj.save()
                    n -= 1
                    continue

                i = 1
                error_tag = 0
                goods_orders = obj.togoods_set.all()
                for goods_order in goods_orders:
                    try:
                        account_order = goods_order.tailtoaccount.account_order
                    except:
                        account_order = AccountInfo()
                    copy_fields_order = ['shop', 'order_category', 'mode_warehouse', 'sent_consignee',
                                         'sign_company', 'sign_department', 'sent_smartphone', 'message']
                    for key in copy_fields_order:
                        value = getattr(obj, key, None)
                        setattr(account_order, key, value)

                    copy_fields_goods = ['goods_id', 'goods_name', 'goods_nickname', 'quantity',
                                         'settlement_price', 'settlement_amount']

                    for key in copy_fields_goods:
                        value = getattr(goods_order, key, None)
                        setattr(account_order, key, value)

                    account_order.creator = obj.creator
                    account_order.order_id = "%s-%s-%s" % (obj.order_id, i, goods_order.goods_id)
                    i += 1
                    account_order.submit_time = datetime.datetime.now()
                    pb2acc_order = TailTOAccount()
                    pb2acc_order.tail_goods = goods_order
                    try:
                        account_order.save()
                        pb2acc_order.account_order = account_order
                        pb2acc_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成结算单出错 %s" % (obj.order_id, e))
                        obj.mistake_tag = 2
                        obj.save()
                        error_tag = 1
                        break
                if error_tag:
                    continue
                expense_order = obj.tailtoexpense.expense
                statement = Statements()
                _q_verifyexpense = VerificationExpenses.objects.filter(expense=expense_order)
                if _q_verifyexpense:
                    data["error"].append("%s 支出流水创建重复，联系管理员处理" % obj.order_id)
                    obj.mistake_tag = 5
                    obj.save()
                    continue
                statement.order_id = "S" + expense_order.order_id
                statement.account = expense_order.account
                statement.category = expense_order.category
                statement.expenses = expense_order.amount
                statement.creator = obj.creator
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
                verifyexpense.creator = obj.creator
                try:
                    statement.save()
                    verifyexpense.statement = statement
                    verifyexpense.save()
                except Exception as e:
                    data["error"].append("%s 支出流水单错误 %s" % (obj.order_id, e))
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                all_prestores = Prestore.objects.filter(account=expense_order.account, order_status=3)
                charge_amount = expense_order.amount
                error_tag = 0
                for prestore in all_prestores:
                    if prestore.remaining > charge_amount:
                        prestore.remaining = round(prestore.remaining - charge_amount, 2)
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = round(charge_amount - prestore.remaining, 2)
                        prestore.remaining = 0
                        prestore.order_status = 4
                        actual_amount = prestore.remaining
                    expendlist = ExpendList()
                    expendlist.statements = statement
                    expendlist.account = expense_order.account
                    expendlist.prestore = prestore
                    expendlist.amount = actual_amount
                    expendlist.creator = obj.creator
                    try:
                        prestore.save()
                        expendlist.save()
                    except Exception as e:
                        data["error"].append("%s 支出划账错误 %s" % (obj.order_id, e))
                        obj.mistake_tag = 7
                        obj.save()
                        error_tag = 1
                        break
                    if charge_amount == 0:
                        break
                if error_tag:
                    continue
                expense_order.order_status = 2
                expense_order.save()
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 4
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
                if obj.mistake_tag in [0, 1]:
                    data["error"].append("%s 非异常状态订单不可修复" % obj.order_id)
                    continue
                i = 1
                goods_orders = obj.togoods_set.all()
                for goods_order in goods_orders:
                    _q_t2a = TailTOAccount.objects.filter(tail_goods=goods_order)
                    if _q_t2a:
                        acc_order = _q_t2a[0].account_order
                    else:
                        acc_order = AccountInfo()
                    copy_fields_order = ['shop', 'order_category', 'mode_warehouse', 'sent_consignee',
                                         'sign_company', 'sign_department', 'sent_smartphone', 'message']

                    for key in copy_fields_order:
                        value = getattr(obj, key, None)
                        setattr(acc_order, key, value)

                    copy_fields_goods = ['goods_id', 'goods_name', 'goods_nickname', 'quantity',
                                         'settlement_price', 'settlement_amount']

                    for key in copy_fields_goods:
                        value = getattr(goods_order, key, None)
                        setattr(acc_order, key, value)

                    acc_order.creator = self.request.user.username
                    if not acc_order.order_id:
                        acc_order.order_id = "%s-%s-%s" % (obj.order_id, i, goods_order.goods_id)
                    i += 1
                    acc_order.submit_time = datetime.datetime.now()
                    pb2acc_order = TailTOAccount()
                    pb2acc_order.tail_goods = goods_order
                    try:
                        acc_order.save()
                        pb2acc_order.account_order = acc_order
                        pb2acc_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成对账单出错 %s" % (obj.order_id, e))
                        obj.mistake_tag = 2
                        obj.save()
                        break
                expense_order = obj.tailtoexpense.expense
                _q_verifyexpense = VerificationExpenses.objects.filter(expense=expense_order)
                if _q_verifyexpense:
                    statement = _q_verifyexpense[0].statement
                else:
                    statement = Statements()
                if not statement.order_id:
                    statement.order_id = "S" + expense_order.order_id
                statement.account = expense_order.account
                statement.category = expense_order.category
                statement.expenses = expense_order.amount
                statement.creator = obj.creator
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
                verifyexpense.creator = obj.creator
                try:
                    statement.save()
                    verifyexpense.statement = statement
                    verifyexpense.save()
                except Exception as e:
                    data["error"].append("%s 支出流水单错误 %s" % (obj.order_id, e))
                    obj.mistake_tag = 6
                    obj.save()
                    continue
                try:
                    charged_amount = ExpendList.objects.filter(Statements=statement).aggregate(Sum("amount"))["amount__sum"]
                except Exception as e:
                    charged_amount = 0
                if not charged_amount:
                    charged_amount = 0
                all_prestores = Prestore.objects.filter(account=expense_order.account, order_status=3)
                charge_amount = round(expense_order.amount - charged_amount, 2)
                error_tag = 0
                for prestore in all_prestores:
                    if prestore.remaining > charge_amount:
                        prestore.remaining = round(prestore.remaining - charge_amount, 2)
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = round(charge_amount - prestore.remaining, 2)
                        prestore.remaining = 0
                        prestore.order_status = 4
                        actual_amount = prestore.remaining
                    expendlist = ExpendList()
                    expendlist.statements = statement
                    expendlist.account = expense_order.account
                    expendlist.prestore = prestore
                    expendlist.amount = actual_amount
                    expendlist.creator = request.user.username
                    try:
                        expendlist.save()
                        prestore.save()
                    except Exception as e:
                        data["error"].append("%s 支出划账错误 %s" % (obj.order_id, e))
                        obj.mistake_tag = 7
                        obj.save()
                        error_tag = 1
                        break
                    if charge_amount == 0:
                        break
                if error_tag:
                    continue
                expense_order.order_status = 2
                expense_order.save()
                obj.order_status = 2
                obj.mistake_tag = 0
                obj.process_tag = 4

                obj.save()

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                params["sign_department"] = user.department
            else:
                params["creator"] = user.username
        params = request.query_params
        f = TailOrderFilter(params)
        serializer = TailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


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
                if obj.process_tag == 4:
                    data["error"].append("%s 存在已经标记发货的明细，不可以驳回！" % obj.order_id)
                    n -= 1
                    continue
                if obj.order_status > 0:
                    obj.order_status -= 1
                    obj.process_tag = 5
                    obj.save()
                    if obj.order_status == 0:
                        obj.togoods_set.all().delete()
                        _q_tail_orders = obj.ori_tail_order.tailorder_set.all().filter(order_status__in=[1, 2, 3])
                        if _q_tail_orders.exists():
                            data["error"].append("%s 取消成功，但是还存在其他子订单未驳回，源订单无法被驳回" % obj.order_id)
                            obj.ori_tail_order.process_tag = 7
                            obj.ori_tail_order.save()
                        else:
                            obj.ori_tail_order.order_status = 2
                            obj.ori_tail_order.process_tag = 5

                            obj.ori_tail_order.save()
                        expense = obj.tailtoexpense.expense
                        expense.order_status = 0
                        expense.save()
                    else:
                        data["error"].append("%s 驳回上一级成功" % obj.order_id)

                else:
                    n -= 1
                    data["error"].append("%s 单据状态错误，请检查，驳回出错。" % obj.order_id)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {"原始单号": "order_id", "物流单号": "track_no"}
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0)
                FILTER_FIELDS = ['原始单号', '物流单号']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    columns_key[i] = columns_key[i].replace(' ', '').replace('=', '')

                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = TailOrder.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic["error"].append(str(_ret_verify_field))
                    return report_dic

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
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                    i += 1
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        for order in resource:
            try:
                TailOrder.objects.filter(order_id=order["order_id"], order_status=1, mode_warehouse=0).update(track_no=order["track_no"])
                report_dic["successful"] += 1
            except Exception as e:
                report_dic["false"] += 1
                report_dic["error"].append(e)
        return report_dic


class TOGoodsSpecialViewset(viewsets.ModelViewSet):
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
    serializer_class = TOGoodsSerializer
    filter_class = TOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_togoods',]
    }

    def get_queryset(self):
        if not self.request:
            return TOGoods.objects.none()
        queryset = TOGoods.objects.filter(is_delete=0, tail_order__order_status=1, tail_order__mode_warehouse=0).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["process_tag"] = 0
        params["tail_order__mode_warehouse"] = 0
        params["tail_order__order_status"] = 1
        f = TOGoodsFilter(params)
        serializer = TOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = TOGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = TOGoods.objects.filter(id__in=order_ids)
            else:
                handle_list = []
        return handle_list

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
            check_list.update(process_tag=4)
            for goods_order in check_list:
                _q_status = goods_order.tail_order.togoods_set.all().filter(process_tag=0)
                if _q_status.exists():
                    goods_order.tail_order.process_tag = 3
                else:
                    goods_order.tail_order.process_tag = 4
                goods_order.tail_order.save()
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
            for goods_order in check_list:
                goods_order.tail_order.process_tag = 0
                goods_order.tail_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)


class TailOrderViewset(viewsets.ModelViewSet):
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
    serializer_class = TailOrderSerializer
    filter_class = TailOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_tailorder',]
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = TailOrder.objects.all().order_by("id")
        else:
            queryset = TailOrder.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = TailOrderFilter(params)
        serializer = TailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


class TOGoodsViewset(viewsets.ModelViewSet):
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
    serializer_class = TOGoodsSerializer
    filter_class = TOGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_togoods',]
    }

    def get_queryset(self):
        if not self.request:
            return TOGoods.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = TOGoods.objects.all().order_by("-id")
        else:
            queryset = TOGoods.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                params["sign_department"] = user.department
            else:
                params["creator"] = user.username
        f = TOGoodsFilter(params)
        serializer = TOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)


class RefundOrderSubmitViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundOrderSerializer
    filter_class = RefundOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_user_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return RefundOrder.objects.none()
        user = self.request.user
        queryset = RefundOrder.objects.filter(creator=user.username, order_status=1).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                params["sign_department"] = user.department
            else:
                params["creator"] = user.username
        f = RefundOrderFilter(params)
        serializer = RefundOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = RefundOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = RefundOrder.objects.filter(id__in=order_ids, order_status=1)
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
            for refund_order in check_list:
                if refund_order.tail_order.order_status != 2:
                    data["error"].append("%s 关联的尾货单还未发货" % refund_order.order_id)
                    refund_order.mistake_tag = 13
                    refund_order.save()
                    n -= 1
                    continue
                if not refund_order.track_no:
                    data["error"].append("%s 没退回快递信息" % refund_order.order_id)
                    refund_order.mistake_tag = 4
                    refund_order.save()
                    n -= 1
                    continue
                _q_track_no_repeat = RefundOrder.objects.filter(track_no=refund_order.track_no)
                if len(_q_track_no_repeat) > 1:
                    data["error"].append("%s 此单退回单号重复" % refund_order.order_id)
                    refund_order.mistake_tag = 15
                    refund_order.save()
                    n -= 1
                    continue
                if not refund_order.info_refund:
                    data["error"].append("%s 此单还没有退换原因" % refund_order.order_id)
                    refund_order.mistake_tag = 3
                    refund_order.save()
                    n -= 1
                    continue
                if refund_order.amount > refund_order.tail_order.amount:
                    data["error"].append("%s 退换金额超出原单金额" % refund_order.order_id)
                    refund_order.mistake_tag = 2
                    refund_order.save()
                    n -= 1
                    continue
                if refund_order.quantity > refund_order.tail_order.quantity:
                    data["error"].append("%s 退换数量超出原单数量" % refund_order.order_id)
                    refund_order.mistake_tag = 1
                    refund_order.save()
                    n -= 1
                    continue
                if refund_order.order_category != 3:
                    data["error"].append("%s 现阶段只支持退货单，更正为退货单" % refund_order.order_id)
                    refund_order.mistake_tag = 14
                    refund_order.save()
                    n -= 1
                    continue
                try:
                    prestore_order = refund_order.refundtoprestore.prestore
                    if prestore_order.order_status != 1:
                        data["error"].append("%s 关联预存单出错" % refund_order.order_id)
                        refund_order.mistake_tag = 10
                        refund_order.save()
                        n -= 1
                        continue
                    else:
                        prestore_order.order_status = 2
                except:
                    prestore_order = Prestore()
                    prestore_order.order_status = 2
                try:
                    prestore_order.account = request.user.account
                except:
                    data["error"].append("%s 当前登录人无预存账户" % refund_order.order_id)
                    refund_order.mistake_tag = 11
                    refund_order.save()
                    n -= 1
                    continue
                prestore_order.order_id = "P" + refund_order.order_id
                prestore_order.bank_sn = refund_order.order_id
                prestore_order.category = 2
                prestore_order.amount = refund_order.amount
                prestore_order.memorandum = "源自退款单：%s" % refund_order.order_id
                prestore_order.creator = refund_order.creator
                try:
                    prestore_order.save()
                    try:
                        refundtoprestore = refund_order.refundtoprestore
                    except:
                        refundtoprestore = RefundToPrestore()
                    refundtoprestore.refund_order = refund_order
                    refundtoprestore.prestore = prestore_order
                    refundtoprestore.creator = refund_order.creator
                    refundtoprestore.save()
                except Exception as e:
                    data["error"].append("%s 创建预存单错误" % refund_order.order_id)
                    refund_order.mistake_tag = 12
                    refund_order.save()
                    n -= 1
                    continue

                refund_order.submit_time = datetime.datetime.now()
                refund_order.order_status = 2
                refund_order.mistake_tag = 0
                refund_order.process_tag = 0
                refund_order.save()
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
                try:
                    prestore_order = obj.refundtoprestore.prestore
                    if prestore_order.order_status > 2:
                        data["error"].append("%s 关联预存单出错,不可驳回，联系管理员" % obj.order_id)
                        obj.mistake_tag = 10
                        obj.save()
                        n -= 1
                        continue
                    else:
                        prestore_order.order_stauts = 0
                        prestore_order.save()
                except:
                    pass
                obj.rogoods_set.all().delete()
                obj.order_status = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class RefundOrderCheckViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundOrderSerializer
    filter_class = RefundOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return RefundOrder.objects.none()
        queryset = RefundOrder.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        params["order_status"] = 2
        f = RefundOrderFilter(params)
        serializer = RefundOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = RefundOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = RefundOrder.objects.filter(id__in=order_ids, order_status=2)
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
            for refund_order in check_list:
                try:
                    if refund_order.process_tag != 4:
                        data["error"].append("%s 货品单据未入库" % refund_order.order_id)
                        refund_order.mistake_tag = 7
                        refund_order.save()
                        n -= 1
                        continue
                    prestore_order = refund_order.refundtoprestore.prestore
                    if prestore_order.order_status != 2:
                        data["error"].append("%s 关联预存单出错" % refund_order.order_id)
                        refund_order.mistake_tag = 10
                        refund_order.save()
                        n -= 1
                        continue
                    else:
                        prestore_order.remaining = prestore_order.amount
                        prestore_order.order_status = 3
                        prestore_order.save()
                except:
                    data["error"].append("%s 关联预存单出错" % refund_order.order_id)
                    refund_order.mistake_tag = 10
                    refund_order.save()
                    n -= 1
                    continue
                goods_orders = refund_order.rogoods_set.all()
                i = 1
                error_tag = 0
                for goods_order in goods_orders:
                    try:
                        account_order = goods_order.rogoodstoaccount.account_order
                    except:
                        account_order = AccountInfo()
                    copy_fields_order = ['shop', 'order_category', 'mode_warehouse', 'sent_consignee',
                                         'sign_company', 'sign_department', 'sent_smartphone', 'message']

                    for key in copy_fields_order:
                        value = getattr(refund_order, key, None)
                        setattr(account_order, key, value)

                    copy_fields_goods = ['goods_id', 'goods_name', 'goods_nickname',
                                         'settlement_price']

                    for key in copy_fields_goods:
                        value = getattr(goods_order, key, None)
                        setattr(account_order, key, value)
                    account_order.quantity = goods_order.receipted_quantity
                    account_order.settlement_amount = -goods_order.settlement_amount
                    account_order.creator = refund_order.creator
                    account_order.order_id = "%s-%s-%s" % (refund_order.order_id, i, goods_order.goods_id)
                    i += 1
                    account_order.submit_time = datetime.datetime.now()
                    rog2acc_order = ROGoodsToAccount()
                    rog2acc_order.ro_order = goods_order
                    try:
                        account_order.save()
                        rog2acc_order.account_order = account_order
                        rog2acc_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成结算单出错 %s" % (refund_order.order_id, e))
                        refund_order.mistake_tag =18
                        refund_order.save()
                        n -= 1
                        error_tag = 1
                        break
                if error_tag:
                    continue
                refund_order.handle_time = datetime.datetime.now()
                start_time = datetime.datetime.strptime(str(refund_order.submit_time).split(".")[0],
                                                        "%Y-%m-%d %H:%M:%S")
                end_time = datetime.datetime.strptime(str(refund_order.handle_time).split(".")[0],
                                                      "%Y-%m-%d %H:%M:%S")
                d_value = end_time - start_time
                days_seconds = d_value.days * 3600
                total_seconds = days_seconds + d_value.seconds
                refund_order.handle_interval = math.floor(total_seconds / 60)
                refund_order.order_status = 3
                refund_order.mistake_tag = 0
                refund_order.save()
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
                _q_ro_goods = obj.rogoods_set.all()
                mistake_tag = 0
                for rogoods in _q_ro_goods:
                    if rogoods.order_status > 2 or rogoods.receipted_quantity > 0:
                        mistake_tag = 1
                        break
                if mistake_tag:
                    data["error"].append("%s 已存在关联入库，不可以驳回" % obj.order_id)
                    obj.mistake_tag = 5
                    obj.save()
                    n -= 1
                    continue
                try:
                    prestore_order = obj.refundtoprestore.prestore
                    if prestore_order.order_status > 2:
                        data["error"].append("%s 关联预存单出错,不可驳回，联系管理员" % obj.order_id)
                        obj.mistake_tag = 10
                        obj.save()
                        n -= 1
                        continue
                    else:
                        prestore_order.order_status = 1
                        prestore_order.save()
                except:
                    data["error"].append("%s 关联预存单出错,不可驳回，联系管理员" % obj.order_id)
                    obj.mistake_tag = 10
                    obj.save()
                    n -= 1
                    continue
                _q_ro_goods.update(order_status=1)
                obj.order_status = 1
                obj.save()
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_handled(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=2)
            for obj in check_list:
                obj.process_tag = 2
                obj.save()
                obj.rogoods_set.all().update(order_status=2)
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
            for obj in check_list:
                goods_details = obj.rogoods_set.all()
                mistake_tag = 0
                for goods in goods_details:
                    if goods.process_tag !=0:
                        mistake_tag = 1
                        break
                if mistake_tag:
                    data["error"].append("%s 入库单已经操作，不可以清除标记" % obj.order_id)
                    obj.mistake_tag = 16
                    obj.save()
                    n -= 1
                    continue
                goods_details.update(order_status=1)
                obj.process_tag = 0
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)


class RefundOrderAuditViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundOrderSerializer
    filter_class = RefundOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_user_refundorder',]
    }

    def get_queryset(self):
        user = self.request.user
        if not self.request:
            return RefundOrder.objects.none()
        queryset = RefundOrder.objects.filter(order_status=3, creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        params["creator"] = user.username
        params["order_status"] = 3
        f = RefundOrderFilter(params)
        serializer = RefundOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = RefundOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = RefundOrder.objects.filter(id__in=order_ids, order_status=3)
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
            check_list.update(order_status=4)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)


class RefundOrderManageViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundOrderSerializer
    filter_class = RefundOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return RefundOrder.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = RefundOrder.objects.all().order_by("-id")
        else:
            queryset = RefundOrder.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = RefundOrderFilter(params)
        serializer = RefundOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


class ROGoodsReceivalViewset(viewsets.ModelViewSet):
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
    serializer_class = ROGoodsSerializer
    filter_class = ROGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_check_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return ROGoods.objects.none()
        queryset = ROGoods.objects.filter(order_status=2).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = ROGoodsFilter(params)
        serializer = ROGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        if all_select_tag:
            handle_list = ROGoodsFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = ROGoods.objects.filter(id__in=order_ids)
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
                if obj.process_tag != 4:
                    data["error"].append("%s 入库单未确认" % obj.goods_nickname)
                    obj.mistake_tag = 3
                    obj.save()
                    n -= 1
                    continue
                if obj.receipted_quantity != obj.quantity:
                    data["error"].append("%s 入库数和待收货数不符" % obj.goods_nickname)
                    obj.mistake_tag = 2
                    obj.save()
                    n -= 1
                    continue
                if obj.receipted_quantity == 0:
                    data["error"].append("%s 入库数量是0" % obj.goods_nickname)
                    obj.mistake_tag = 2
                    obj.save()
                    n -= 1
                    continue
                refund_quantity = obj.refund_order.rogoods_set.all().aggregate(Sum("receipted_quantity"))["receipted_quantity__sum"]
                if refund_quantity != obj.refund_order.quantity:
                    data["error"].append("%s 退款单未完整入库" % obj.refund_order.order_id)
                    obj.mistake_tag = 4
                    obj.save()
                    n -= 1
                    continue

                obj.order_status = 3
                obj.save()
                obj.refund_order.process_tag = 4
                obj.refund_order.save()

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_handled(self, request, *args, **kwargs):
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=4)
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
            check_list.update(process_tag=0, receipted_quantity=0)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        return Response(data)


class ROGoodsManageViewset(viewsets.ModelViewSet):
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
    serializer_class = ROGoodsSerializer
    filter_class = ROGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return ROGoods.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = ROGoods.objects.all().order_by("-id")
        else:
            queryset = ROGoods.objects.filter(creator=user.username).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["creator"] = user.username
        f = ROGoodsFilter(params)
        serializer = ROGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)


class AccountInfoViewset(viewsets.ModelViewSet):
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
    serializer_class = AccountInfoSerializer
    filter_class = AccountInfoFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_accountinfo', ]
    }

    def get_queryset(self):
        if not self.request:
            return AccountInfo.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = AccountInfo.objects.all().order_by("-id")
        else:
            queryset = AccountInfo.objects.filter(sign_company=user.company).order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if not user.is_our:
                params["sign_company"] = user.company
        f = AccountInfoFilter(params)
        serializer = AccountInfoSerializer(f.qs, many=True)
        return Response(serializer.data)


class TailToExpenseViewset(viewsets.ModelViewSet):
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
    serializer_class = TailToExpenseSerializer
    filter_class = TailToExpenseFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return TailToExpense.objects.none()
        user = self.request.user
        queryset = TailToExpense.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        params = request.data
        params.pop("page", None)
        params.pop("allSelectTag", None)
        f = TailToExpenseFilter(params)
        serializer = TailToExpenseSerializer(f.qs, many=True)
        return Response(serializer.data)


class RefundToPrestoreViewset(viewsets.ModelViewSet):
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
    serializer_class = RefundToPrestoreSerializer
    filter_class = RefundToPrestoreFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['tailgoods.view_handler_refundorder',]
    }

    def get_queryset(self):
        if not self.request:
            return RefundToPrestore.objects.none()
        user = self.request.user
        queryset = RefundToPrestore.objects.all().order_by("-id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.query_params
        f = RefundToPrestoreFilter(params)
        serializer = RefundToPrestoreSerializer(f.qs, many=True)
        return Response(serializer.data)






