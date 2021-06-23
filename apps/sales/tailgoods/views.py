import re, datetime
import math
from django.db.models import Avg,Sum,Max,Min
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .serializers import OriTailOrderSerializer, OTOGoodsSerializer, TailOrderSerializer, TOGoodsSerializer, \
    RefundOrderSerializer, ROGoodsSerializer, AccountInfoSerializer, TailPartsOrderSerializer, TailToExpenseSerializer
from .filters import OriTailOrderFilter, OTOGoodsFilter, TailOrderFilter, TOGoodsFilter, RefundOrderFilter, \
    ROGoodsFilter, AccountInfoFilter, TailPartsOrderFilter, TailToExpenseFilter
from .models import OriTailOrder, OTOGoods, TailOrder, TOGoods, RefundOrder, ROGoods, AccountInfo, TailPartsOrder, \
    TailToExpense, TailTOAccount
from apps.sales.advancepayment.models import Expense, Account, Statements, VerificationExpenses, ExpendList, Prestore
from apps.auth.users.models import UserProfile
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response


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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        user = self.request.user
        queryset = OriTailOrder.objects.filter(creator=user.username, order_status=1).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        request.data["creator"] = user.username
        params = request.query_params
        f = OriTailOrderFilter(params)
        serializer = OriTailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriTailOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriTailOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }

        if n:
            for obj in check_list:
                user = UserProfile.objects.filter(username=obj.creator)[0]
                _q_account = Account.objects.filter(user=user)
                if not _q_account:
                    data["error"].append("%s 单据创建人不存在预存账户" % obj.order_id)
                    obj.mistake_tag = 17
                    obj.save()
                    continue
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
                _q_repeated_order = OriTailOrder.objects.filter(sent_consignee=obj.sent_consignee,
                                                                order_status__in=[2, 3, 4])
                if _q_repeated_order.exists():
                    if obj.process_tag != 10:
                        data["error"].append("%s 重复提交的订单" % obj.order_id)
                        obj.mistake_tag = 15
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_used(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=8)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_retread(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=9)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_special(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=10)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def recover(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=0)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        queryset = OriTailOrder.objects.filter(order_status=2).order_by("id")
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

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = OriTailOrderFilter(params)
        serializer = OriTailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
                tail_order.creator = self.request.user.username
                tail_order.ori_amount = obj.amount
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
                        to_good.settlement_price = to_good.price * obj.sign_company.discount_rate
                        to_good.settlement_amount = to_good.settlement_price * to_good.quantity
                        amount += to_good.settlement_amount
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
                    verify_order.creator = request.user.username
                    verify_order.save()
                tail_order.amount = amount
                tail_order.save()
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 2
                obj.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def check_split(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
                                             'message', 'sign_company', 'sign_department']
                        for key in copy_fields_order:
                            value = getattr(obj, key, None)
                            setattr(tail_order, key, value)

                        tail_order.sent_province = obj.sent_city.province
                        tail_order.creator = self.request.user.username
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
                            goods_order.goods_nickname = goods.goods_name
                            goods_order.goods_id = goods.goods_id
                            goods_order.quantity = 1
                            goods_order.price = price
                            goods_order.amount = price
                            goods_order.settlement_price = price * obj.sign_company.discount_rate
                            goods_order.settlement_amount = price * obj.sign_company.discount_rate
                            current_amount = goods_order.amount
                            goods_order.memorandum = '来源 %s 的第 %s 个订单' % (obj.order_id, tail_num + 1)

                            try:
                                goods_order.creator = self.request.user.username
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
                            verify_order.creator = request.user.username
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
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def set_logistics(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=6)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def recover(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            check_list.update(process_tag=1)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=1)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["success"] = n
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriTailOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = OriTailOrder.objects.all().order_by("id")
        else:
            queryset = OriTailOrder.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OTOGoods.objects.none()
        user = self.request.user
        if user.category:
            queryset = OTOGoods.objects.all().order_by("id")
        else:
            queryset = OTOGoods.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        queryset = TailOrder.objects.filter(mode_warehouse=1, order_status=1).order_by("id")
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
                handle_list = TailOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list


    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
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
                        prestore.remaining = prestore.remaining - charge_amount
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = charge_amount - prestore.remaining
                        prestore.remaining = 0
                        prestore.order_status = 4
                        actual_amount = prestore.remaining
                    expendlist = ExpendList()
                    expendlist.Statements = statement
                    expendlist.account = expense_order.account
                    expendlist.prestore = prestore
                    expendlist.amount = actual_amount
                    expendlist.creator = request.user.username
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
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 4

                obj.save()



                print(obj)
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def fix(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "success": 0,
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
                verifyexpense = VerificationExpenses()
                verifyexpense.expense = expense_order
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
                charge_amount = expense_order.amount - charged_amount
                error_tag = 0
                for prestore in all_prestores:
                    if prestore.remaining > charge_amount:
                        prestore.remaining = prestore.remaining - charge_amount
                        actual_amount = charge_amount
                        charge_amount = 0
                    else:
                        charge_amount = charge_amount - prestore.remaining
                        prestore.remaining = 0
                        prestore.order_status = 4
                        actual_amount = prestore.remaining
                    expendlist = ExpendList()
                    expendlist.Statements = statement
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
                obj.order_status = 3
                obj.mistake_tag = 0
                obj.process_tag = 4

                obj.save()

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["success"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
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
            "success": 0,
            "false": 0,
            "error": []
        }
        if n:
            for obj in reject_list:
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
                            data["error"].append("%s 取消成功，并且源订单驳回到待审核状态" % obj.order_id)
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
        data["success"] = n
        return Response(data)


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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TOGoods.objects.none()
        queryset = TOGoods.objects.filter(is_delete=0, tail_order__order_status=1, tail_order__mode_warehouse=1).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.query_params
        f = TOGoodsFilter(params)
        serializer = TOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)


class TailOrderSpecialViewset(viewsets.ModelViewSet):
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = TailOrder.objects.all().order_by("id")
        else:
            queryset = TailOrder.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = TailOrderFilter(params)
        serializer = TailOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TailOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = TailOrder.objects.all().order_by("id")
        else:
            queryset = TailOrder.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TOGoods.objects.none()
        user = self.request.user
        if user.category:
            queryset = TOGoods.objects.all().order_by("id")
        else:
            queryset = TOGoods.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = TOGoodsFilter(params)
        serializer = TOGoodsSerializer(f.qs, many=True)
        return Response(serializer.data)


class RefundOrderViewset(viewsets.ModelViewSet):
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return RefundOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = RefundOrder.objects.all().order_by("id")
        else:
            queryset = RefundOrder.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = RefundOrderFilter(params)
        serializer = RefundOrderSerializer(f.qs, many=True)
        return Response(serializer.data)


class ROGoodsViewset(viewsets.ModelViewSet):
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return ROGoods.objects.none()
        user = self.request.user
        if user.category:
            queryset = ROGoods.objects.all().order_by("id")
        else:
            queryset = ROGoods.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return AccountInfo.objects.none()
        user = self.request.user
        if user.category:
            queryset = AccountInfo.objects.all().order_by("id")
        else:
            queryset = AccountInfo.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = AccountInfoFilter(params)
        serializer = AccountInfoSerializer(f.qs, many=True)
        return Response(serializer.data)


class TailPartsOrderViewset(viewsets.ModelViewSet):
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
    serializer_class = TailPartsOrderSerializer
    filter_class = TailPartsOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TailPartsOrder.objects.none()
        user = self.request.user
        if user.category:
            queryset = TailPartsOrder.objects.all().order_by("id")
        else:
            queryset = TailPartsOrder.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.category:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = TailPartsOrderFilter(params)
        serializer = TailPartsOrderSerializer(f.qs, many=True)
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
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return TailToExpense.objects.none()
        user = self.request.user
        queryset = TailToExpense.objects.all().order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.query_params
        f = TailToExpenseFilter(params)
        serializer = TailToExpenseSerializer(f.qs, many=True)
        return Response(serializer.data)







