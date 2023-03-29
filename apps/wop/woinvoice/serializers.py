# -*- coding: utf-8 -*-
# @Time    : 2020/12/24 15:23
# @Author  : Hann
# @Site    : 
# @File    : serializers.py
# @Software: PyCharm

import re
import datetime
import jieba
from functools import reduce
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
from .models import OriInvoice, OriInvoiceGoods, Invoice, InvoiceGoods, DeliverOrder
from apps.base.goods.models import Goods
from rest_framework import status
from apps.utils.geography.tools import PickOutAdress
from apps.utils.geography.models import Province, City, District

class OriInvoiceSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    submit_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    handle_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = OriInvoice
        fields = "__all__"

    def get_order_category(self, instance):
        category = {
            1: '专票',
            2: '普票'
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '开票中',
            2: '已开票',
            3: '待买票',
            4: '信息错',
            5: '被驳回',
            6: '已处理',
            7: '未申请',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "没开票公司",
            2: "货品错误",
            3: "专票信息缺",
            4: "收件手机错",
            5: "超限额发票",
            6: "递交发票订单出错",
            7: "生成发票货品出错",
            8: "单货品超限额非法",
            9: "发票订单生成重复",
            10: "生成发票订单出错",
            11: "生成发票订单货品出错",
            12: "单据被驳回",
            13: "税号错误",
            14: "源单号格式错误",
            15: "导入货品错误",
            16: "源单号格式错误",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "申请未报",
            2: "正在审核",
            3: "单据生成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_company(self, instance):
        try:
            ret = {
                "id": instance.company.id,
                "name": instance.company.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sent_city(self, instance):
        try:
            ret = {
                "id": instance.sent_city.id,
                "name": instance.sent_city.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign_company(self, instance):
        try:
            ret = {
                "id": instance.sign_company.id,
                "name": instance.sign_company.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign_department(self, instance):
        try:
            ret = {
                "id": instance.sign_department.id,
                "name": instance.sign_department.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.oriinvoicegoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods_id": goods_detail.goods_id,
                "name": {
                    "id": goods_detail.goods_name.id,
                    "name": goods_detail.goods_name.name
                },
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(OriInvoiceSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["shop"] = self.get_shop(instance)
        ret["company"] = self.get_company(instance)
        ret["sent_city"] = self.get_sent_city(instance)
        ret["sign_company"] = self.get_sign_company(instance)
        ret["sign_department"] = self.get_sign_department(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        goods_details = validated_data.pop("goods_details", [])
        amount = self.check_goods_details(goods_details)
        validated_data["amount"] = amount
        if self.context["request"].user.company and self.context["request"].user.department:
            validated_data["sign_company"] = self.context["request"].user.company
            validated_data["sign_department"] = self.context["request"].user.department
        else:
            raise serializers.ValidationError("登陆账号没有设置公司或者部门，不可以创建！")

        user = self.context["request"].user
        validated_data["creator"] = user.username

        _spilt_addr = PickOutAdress(validated_data['sent_address'])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        _rt_addr["district"] = _rt_addr["district"].name
        cs_info_fields = ["city", "district", "address"]
        order_cs_fields = ["sent_city", "sent_district", "sent_address"]
        for i in range(len(cs_info_fields)):
            validated_data[order_cs_fields[i]] = _rt_addr.get(cs_info_fields[i], None)
        if '集运' in str(_rt_addr["address"]):
            raise serializers.ValidationError("地址是集运仓")

        ori_invoice = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail['invoice'] = ori_invoice
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return ori_invoice

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        goods_details = validated_data.pop("goods_details", [])
        amount = self.check_goods_details(goods_details)
        create_time = validated_data.pop("create_time", "")
        if validated_data.get("amount", None) is not None:
            validated_data["amount"] = amount
        if validated_data.get('sent_address', None) is not None:
            _spilt_addr = PickOutAdress(validated_data['sent_address'])
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            _rt_addr["district"] = _rt_addr["district"].name
            cs_info_fields = ["city", "district", "address"]
            order_cs_fields = ["sent_city", "sent_district", "sent_address"]
            for i in range(len(cs_info_fields)):
                validated_data[order_cs_fields[i]] = _rt_addr.get(cs_info_fields[i], None)
            if '集运' in str(_rt_addr["address"]):
                raise serializers.ValidationError("地址是集运仓")

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        for goods_detail in goods_details:
            goods_detail['invoice'] = instance
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        # instance.groups.set(groups_list)
        # instance.user_permissions.set(user_permissions)
        return instance

    def check_goods_details(self, goods_details):
        if not goods_details:
            return 0
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("price", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")
        else:
            amount_list = list(map(lambda x: float(x["price"]) * int(x["quantity"]), goods_details))
            amount = reduce(lambda x, y: x + y, amount_list)
            amount = round(amount, 2)
            return amount

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = OriInvoiceGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = OriInvoiceGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail


class OriInvoiceGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)


    class Meta:
        model = OriInvoiceGoods
        fields = "__all__"

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_invoice(self, instance):
        category_dic = {
            1: '专票',
            2: '普票'
        }
        try:
            ret = {
                "id": instance.invoice.id,
                "name": instance.invoice.title,
                "company": instance.invoice.company,
                "order_id": instance.invoice.order_id,
                "order_category": category_dic.get(instance.invoice.order_category, None),
                "title": instance.invoice.title,
                "tax_id": instance.invoice.tax_id,
                "phone": instance.invoice.phone,
                "bank": instance.invoice.bank,
                "account": instance.invoice.account,
                "address": instance.invoice.address,
                "sent_consignee": instance.invoice.sent_consignee,
                "sent_smartphone": instance.invoice.sent_smartphone,
                "sent_address": instance.invoice.sent_address
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(OriInvoiceGoodsSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["invoice"] = self.get_invoice(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        ori_invoice = self.Meta.model.objects.create(**validated_data)
        return ori_invoice

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class InvoiceSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    submit_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    handle_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"

    def validate_invoice_id(self, value):
        if re.match(r'^[\d-]{8,10}$', value) or not value:
            return value
        else:
            raise serializers.ValidationError("发票单号不符合规则！")

    def get_order_category(self, instance):
        category = {
            1: '专票',
            2: '普票'
        }
        ret = {
            "id": instance.order_category,
            "name": category.get(instance.order_category, None)
        }
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '开票中',
            2: '已开票',
            3: '待开票',
            4: '待打单',
            5: '已开票已打单',
            6: '已处理',
            7: '未申请',
        }
        ret = {
            "id": instance.process_tag,
            "name": process.get(instance.process_tag, None)
        }
        return ret

    def get_order_status(self, instance):
        status = {
            0: '已被取消',
            1: '开票处理',
            2: '终审复核',
            3: '工单完结'
        }
        ret = {
            "id": instance.order_status,
            "name": status.get(instance.order_status, None)
        }
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "无发票号或工单未开全",
            2: "快递单错误",
            3: "快递未发货",
            4: "驳回出错",
        }
        ret = {
            "id": instance.mistake_tag,
            "name": mistake_list.get(instance.mistake_tag, None)
        }
        return ret

    def get_shop(self, instance):
        ret = {
            "id": instance.shop.id,
            "name": instance.shop.name
        }
        return ret

    def get_company(self, instance):
        ret = {
            "id": instance.company.id,
            "name": instance.company.name
        }
        return ret

    def get_sent_city(self, instance):
        ret = {
            "id": instance.sent_city.id,
            "name": instance.sent_city.name
        }
        return ret

    def get_sign_company(self, instance):
        ret = {
            "id": instance.sign_company.id,
            "name": instance.sign_company.name
        }
        return ret

    def get_sign_department(self, instance):
        ret = {
            "id": instance.sign_department.id,
            "name": instance.sign_department.name
        }
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.invoicegoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods_id": goods_detail.goods_id,
                "name": {
                    "id": goods_detail.goods_name.id,
                    "name": goods_detail.goods_name.name
                },
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(InvoiceSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        try:
            ret["work_order"] = {
                "id": instance.work_order.id,
                "name": instance.work_order.order_id
            }
            ret["order_category"] = self.get_order_category(instance)
            ret["process_tag"] = self.get_process_tag(instance)

            ret["mistake_tag"] = self.get_mistake_tag(instance)
            ret["shop"] = self.get_shop(instance)
            ret["company"] = self.get_company(instance)
            ret["sent_city"] = self.get_sent_city(instance)
            ret["sign_company"] = self.get_sign_company(instance)
            ret["sign_department"] = self.get_sign_department(instance)
            ret["goods_details"] = self.get_goods_details(instance)
        except:
            error = {"id": -1, "name": "显示错误"}
            ret["work_order"] = error
            ret["order_category"] = error
            ret["process_tag"] = error
            ret["mistake_tag"] = error
            ret["shop"] = error
            ret["company"] = error
            ret["sent_city"] = error
            ret["sign_company"] = error
            ret["sign_department"] = error
            ret["goods_details"] = error
        return ret


class InvoiceGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = InvoiceGoods
        fields = "__all__"


class DeliverOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = DeliverOrder
        fields = "__all__"

    def get_process_tag(self, instance):
        process = {
            0: '待打印',
            1: '已打印',
            2: '暂停发',
        }
        ret = {
            "id": instance.process_tag,
            "name": process.get(instance.process_tag, None)
        }
        return ret

    def get_order_status(self, instance):
        status = {
            0: '已被取消',
            1: '等待打单',
            2: '打印完成',
        }
        ret = {
            "id": instance.order_status,
            "name": status.get(instance.order_status, None)
        }
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "无发票号或工单未开全",
            2: "快递单错误",
            3: "快递未发货",
            4: "驳回出错",
        }
        ret = {
            "id": instance.mistake_tag,
            "name": mistake_list.get(instance.mistake_tag, None)
        }
        return ret

    def to_representation(self, instance):
        ret = super(DeliverOrderSerializer, self).to_representation(instance)
        try:
            ret["work_order"] = {
                "id": instance.work_order.id,
                "name": instance.work_order.order_id
            }
            ret["process_tag"] = self.get_process_tag(instance)
            ret["order_status"] = self.get_order_status(instance)
            ret["mistake_tag"] = self.get_mistake_tag(instance)
        except:
            error = {"id": -1, "name": "显示错误"}
            ret["work_order"] = error
            ret["process_tag"] = error
            ret["order_status"] = error
            ret["mistake_tag"] = error
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance
