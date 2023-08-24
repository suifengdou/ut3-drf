import datetime, re
from django.db.models import Count, Sum, Avg
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import RefundTrialOrder, RTOGoods, LogRefundTrialOrder, LogRTOGoods
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress
from apps.utils.logging.loggings import logging


class RefundTrialOrderSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = RefundTrialOrder
        fields = "__all__"

    def get_ori_order(self, instance):
        try:
            ret = {
                "id": instance.ori_order.id,
                "name": instance.ori_order.manual_order.erp_order_id,
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_express(self, instance):
        try:
            ret = {
                "id": instance.express.id,
                "name": instance.express.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_category(self, instance):
        category_list = {
            1: "退货退款",
            2: "换货退回",
            3: "仅退款",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category_list.get(instance.order_category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "取回方式非逆向取件",
            2: "退货人手机错误",
            3: "收货仓库手机错误",
            4: "收货仓库收货信息缺失",
            5: "已存在关联入库，不可以驳回",
            6: "物流创建接口错误",
            7: "只有未处理状态才可确认快递",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "确认物流",
            2: "获取单号",
            3: "重复单号",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待递交",
            2: "待入库",
            3: "待结算",
            4: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_return_type(self, instance):
        type_list = {
            1: "客户寄回",
            2: "ERP逆向",
            3: "UT德邦逆向",
        }
        try:
            ret = {
                "id": instance.return_type,
                "name": type_list.get(instance.return_type, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.rtogoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods": {
                    "id": goods_detail.goods.id,
                    "name": goods_detail.goods.name
                },
                "quantity": goods_detail.quantity,
                "settlement_price": goods_detail.settlement_price,
                "sn": goods_detail.sn,
                "memo": goods_detail.memo
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(RefundTrialOrderSerializer, self).to_representation(instance)
        ret["ori_order"] = self.get_ori_order(instance)
        ret["shop"] = self.get_shop(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["express"] = self.get_express(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["return_type"] = self.get_return_type(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods", None), goods.get("quantity", None), goods.get("settlement_price", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
            goods["settlement_price"] = re.sub("[,， ]", "", str(goods["settlement_price"]))
            try:
                goods["settlement_price"] = float(goods["settlement_price"])
            except Exception as e:
                raise serializers.ValidationError("价格格式错误！")
        goods_list = list(map(lambda x: x["goods"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = RTOGoods.objects.create(**data)
        else:
            goods_detail = RTOGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):

        user = self.context["request"].user
        validated_data["creator"] = user.username
        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)

        _spilt_addr = PickOutAdress(validated_data["address"])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        cs_info_fields = ["city", "district", "address"]
        for key_word in cs_info_fields:
            validated_data[key_word] = _rt_addr.get(key_word, None)

        order = self.Meta.model.objects.create(**validated_data)
        logging(order, user, LogRefundTrialOrder, "手工创建")
        for goods_detail in goods_details:
            goods_detail['order'] = order
            goods = Goods.objects.filter(id=goods_detail["goods"])[0]
            goods_detail["goods"] = goods
            goods_detail["id"] = "n"
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return order

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        address = validated_data.get("address", None)
        if address:
            _spilt_addr = PickOutAdress(address)
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            cs_info_fields = ["city", "district", "address"]
            for key_word in cs_info_fields:
                validated_data[key_word] = _rt_addr.get(key_word, None)
            if '集运' in str(validated_data["address"]):
                raise serializers.ValidationError("地址是集运仓")
        mobile = validated_data.get("mobile", None)
        if mobile:
            if not re.match(r"^1[23456789]\d{9}$", mobile):
                raise serializers.ValidationError("手机号无法通过验证")
        goods_details = validated_data.pop("goods_details", [])
        if goods_details:
            self.check_goods_details(goods_details)

        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        if goods_details:
            instance.rtogoods_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['order'] = instance
                goods_detail['warehouse'] = instance.warehouse
                _q_goods = Goods.objects.filter(id=goods_detail["goods"])[0]
                goods_detail["goods"] = _q_goods
                goods_detail["settlement_amount"] = float(goods_detail["settlement_price"] * float(goods_detail["quantity"]))
                goods_detail["id"] = 'n'
                goods_detail.pop("xh")
                self.create_goods_detail(goods_detail)
                content.append('更新货品：%s x %s' % (_q_goods.name, goods_detail["quantity"]))
            all_goods = instance.rtogoods_set.all()
            quantity = all_goods.aggregate(quantity=Sum("quantity"))["quantity"]
            amount = all_goods.aggregate(amount=Sum("settlement_amount"))["amount"]
            self.Meta.model.objects.filter(id=instance.id).update(**{
                "quantity": quantity,
                "amount": amount,
            })
        logging(instance, user, LogRefundTrialOrder, "修改内容：%s" % str(content))
        return instance


class RTOGoodsSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = RTOGoods
        fields = "__all__"

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "递交重复",
            2: "保存出错",
            3: "经销商反馈为空",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "经销未递",
            2: "客服在理",
            3: "经销复核",
            4: "运营对账",
            5: "工单完结",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(RTOGoodsSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            data.pop("name", None)
            goods_detail = RefundTrialOrder.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = RefundTrialOrder.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):

        user = self.context["request"].user
        validated_data["creator"] = user.username
        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)
        validated_data["department"] = user.department

        _spilt_addr = PickOutAdress(validated_data["address"])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        cs_info_fields = ["province", "city", "district", "address"]
        for key_word in cs_info_fields:
            validated_data[key_word] = _rt_addr.get(key_word, None)

        order = self.Meta.model.objects.create(**validated_data)
        logging(order, user, LogRefundTrialOrder, "手工创建")
        for goods_detail in goods_details:
            goods_detail['order'] = order
            goods = Goods.objects.filter(id=goods_detail["goods"])[0]
            goods_detail["goods"] = goods
            goods_detail["id"] = "n"
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return order

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["department"] = user.department

        validated_data["updated_time"] = datetime.datetime.now()
        address = validated_data.get("address", None)
        if address:
            _spilt_addr = PickOutAdress(address)
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            cs_info_fields = ["province", "city", "district", "address"]
            for key_word in cs_info_fields:
                validated_data[key_word] = _rt_addr.get(key_word, None)
            if '集运' in str(validated_data["address"]):
                if validated_data["process_tag"] != 3:
                    raise serializers.ValidationError("地址是集运仓")

        goods_details = validated_data.pop("goods_details", [])
        if goods_details:
            self.check_goods_details(goods_details)

        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        if goods_details:
            instance.mogoods_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['manual_order'] = instance
                _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
                goods_detail["goods_name"] = _q_goods
                goods_detail["goods_id"] = _q_goods.goods_id
                goods_detail["id"] = 'n'
                goods_detail.pop("xh")
                self.create_goods_detail(goods_detail)
                content.append('更新货品：%s x %s' % (_q_goods.name, goods_detail["quantity"]))
        logging(instance, user, LogRTOGoods, "修改内容：%s" % str(content))
        return instance



