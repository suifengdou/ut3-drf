import datetime
import jieba
import re
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import IntPurchaseOrder, IPOGoods, ExceptionIPO, EIPOGoods
from apps.base.goods.models import Goods
from apps.int.intaccount.models import Currency, IntAccount


class IntPurchaseOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = IntPurchaseOrder
        fields = "__all__"

    def get_distributor(self, instance):
        try:
            ret = {
                "id": instance.distributor.id,
                "name": instance.distributor.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_account(self, instance):
        try:
            ret = {
                "id": instance.account.id,
                "name": instance.account.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_currency(self, instance):
        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_trade_mode(self, instance):
        mode_list = {
            1: "FOB",
            2: "CIF",
            3: "EXW",
            4: "DDP",
        }
        try:
            ret = {
                "id": instance.trade_mode,
                "name": mode_list.get(instance.trade_mode, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_category(self, instance):
        category_list = {
            1: "样机",
            2: "订单",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category_list.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "待审核",
            2: "待处理",
            3: "待结算",
            4: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_collection_status(self, instance):
        status = {
            0: "未收款",
            1: "已收定",
            2: "已收款",
        }
        try:
            ret = {
                "id": instance.collection_status,
                "name": status.get(instance.collection_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "货品金额为零",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理",
            2: "驳回",
            3: "特殊订单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign(self, instance):
        sign_list = {
            0: "无",
            1: "未排产",
            2: "已排产",
            3: "未发货",
            4: "已发货",
            5: "已完成",
        }
        try:
            ret = {
                "id": instance.sign,
                "name": sign_list.get(instance.sign, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.ipogoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods_id": goods_detail.goods_id,
                "goods_name": {
                    "id": goods_detail.goods_name.id,
                    "name": goods_detail.goods_name.name
                },
                "currency": goods_detail.currency.id,
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(IntPurchaseOrderSerializer, self).to_representation(instance)
        ret["distributor"] = self.get_distributor(instance)
        ret["account"] = self.get_account(instance)
        ret["currency"] = self.get_currency(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["collection_status"] = self.get_collection_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["sign"] = self.get_sign(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["trade_mode"] = self.get_trade_mode(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")
        currency_list = list(map(lambda x: x["currency"], goods_details))
        currency_check = set(currency_list)
        if len(currency_check) != 1:
            raise serializers.ValidationError("明细中币种必须一致！")
        else:
            currency = Currency.objects.filter(id=list(currency_check)[0])[0]
        amount_list = list(map(lambda x: float(x["price"]) * int(x["quantity"]), goods_details))
        quantity_list = list(map(lambda x: int(x["quantity"]), goods_details))
        amount = reduce(lambda x, y: x + y, amount_list)
        quantity = reduce(lambda x, y: x + y, quantity_list)
        return currency, amount, quantity

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = IPOGoods.objects.create(**data)
        else:
            goods_detail = IPOGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):

        user = self.context["request"].user
        validated_data["creator"] = user.username
        goods_details = validated_data.pop("goods_details", [])
        validated_data["currency"], validated_data["amount"], validated_data["quantity"] = self.check_goods_details(goods_details)
        if not user.department:
            raise serializers.ValidationError({"账号问题": "账号必须先配置部门才可建单！" })
        validated_data["department"] = user.department

        instance = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail['ipo'] = instance
            goods_name = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = goods_name
            goods_detail["goods_id"] = goods_name.goods_id
            goods_detail["currency"] = validated_data["currency"]
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return instance

    def check_sign(self, instance, sign):
        if sign in [5, 6, 7, 8, 9, 10]:
            if int(instance.actual_amount) == 0:
                raise serializers.ValidationError({"标记设置错误": "PI单未收款不可选择此标签！"})
        if sign in [11, 12]:
            if instance.virtual_amount != instance.amount:
                raise serializers.ValidationError({"标记设置错误": "PI单未付尾款不可选择此标签！"})

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["department"] = user.department

        validated_data["update_time"] = datetime.datetime.now()

        goods_details = validated_data.pop("goods_details", [])
        if goods_details:
            validated_data["currency"], validated_data["amount"], validated_data["quantity"] = self.check_goods_details(goods_details)
        if validated_data["sign"]:
            self.check_sign(instance, validated_data["sign"])
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        if goods_details:
            instance.ipogoods_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['ipo'] = instance
                _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
                goods_detail["goods_name"] = _q_goods
                goods_detail["goods_id"] = _q_goods.goods_id
                goods_detail["currency"] = validated_data["currency"]
                goods_detail["id"] = 'n'
                goods_detail.pop("xh")
                self.create_goods_detail(goods_detail)
        return instance


class IPOGoodsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = IPOGoods
        fields = "__all__"

    def get_ipo(self, instance):
        category_status = {
            1: "样机",
            2: "订单",
        }
        trade_modes = {
            1: "FOB",
            2: "CIF",
            3: "EXW",
            4: "DDP",
        }
        order_status = {
            0: "已取消",
            1: "待审核",
            2: "待生产",
            3: "待发货",
            4: "待结算",
            5: "已完成",
        }
        collection_status = {
            0: "未收款",
            1: "已收定",
            2: "已收款",
        }
        try:
            ret = {
                "id": instance.ipo.id,
                "order_id": instance.ipo.order_id,
                "distributor": instance.ipo.distributor.name,
                "order_category": category_status.get(instance.ipo.order_category, None),
                "account": instance.ipo.account.name,
                "trade_mode": trade_modes.get(instance.ipo.trade_mode, None),
                "address": instance.ipo.address,
                "contract_id": instance.ipo.contract_id,
                "department": instance.ipo.department.name,
                "order_status": order_status.get(instance.ipo.order_status, None),
                "collection_status": collection_status.get(instance.ipo.collection_status, None),
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_currency(self, instance):
        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未发货",
            2: "已发货",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(IPOGoodsSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["ipo"] = self.get_ipo(instance)
        ret["currency"] = self.get_currency(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ExceptionIPOSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = ExceptionIPO
        fields = "__all__"

    def get_distributor(self, instance):
        try:
            ret = {
                "id": instance.distributor.id,
                "name": instance.distributor.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_currency(self, instance):
        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_trade_mode(self, instance):
        mode_list = {
            1: "FOB",
            2: "CIF",
            3: "EXW",
            4: "DDP",
        }
        try:
            ret = {
                "id": instance.trade_mode,
                "name": mode_list.get(instance.trade_mode, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_category(self, instance):
        category_list = {
            1: "样机",
            2: "订单",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category_list.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "待处理",
            2: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "货品金额为零",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理",
            2: "驳回",
            3: "特殊订单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign(self, instance):
        sign_list = {
            0: "无",
            1: "补货",
            2: "抵货",
            3: "其他",
        }
        try:
            ret = {
                "id": instance.sign,
                "name": sign_list.get(instance.sign, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.eipogoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods_id": goods_detail.goods_id,
                "goods_name": {
                    "id": goods_detail.goods_name.id,
                    "name": goods_detail.goods_name.name
                },
                "currency": goods_detail.currency.id,
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(ExceptionIPOSerializer, self).to_representation(instance)
        ret["distributor"] = self.get_distributor(instance)
        ret["currency"] = self.get_currency(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["sign"] = self.get_sign(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["trade_mode"] = self.get_trade_mode(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")
        currency_list = list(map(lambda x: x["currency"], goods_details))
        currency_check = set(currency_list)
        if len(currency_check) != 1:
            raise serializers.ValidationError("明细中币种必须一致！")
        else:
            currency = Currency.objects.filter(id=list(currency_check)[0])[0]
        amount_list = list(map(lambda x: float(x["price"]) * int(x["quantity"]), goods_details))
        quantity_list = list(map(lambda x: int(x["quantity"]), goods_details))
        amount = reduce(lambda x, y: x + y, amount_list)
        quantity = reduce(lambda x, y: x + y, quantity_list)
        return currency, amount, quantity

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = EIPOGoods.objects.create(**data)
        else:
            goods_detail = EIPOGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):

        user = self.context["request"].user
        validated_data["creator"] = user.username
        goods_details = validated_data.pop("goods_details", [])
        validated_data["currency"], validated_data["amount"], validated_data["quantity"] = self.check_goods_details(goods_details)
        if not user.department:
            raise serializers.ValidationError({"账号问题": "账号必须先配置部门才可建单！" })
        validated_data["department"] = user.department

        instance = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail['ipo'] = instance
            goods_name = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = goods_name
            goods_detail["goods_id"] = goods_name.goods_id
            goods_detail["currency"] = validated_data["currency"]
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return instance

    def check_sign(self, instance, sign):
        if sign in [5, 6, 7, 8, 9, 10]:
            if int(instance.actual_amount) == 0:
                raise serializers.ValidationError({"标记设置错误": "PI单未收款不可选择此标签！"})
        if sign in [11, 12]:
            if instance.virtual_amount != instance.amount:
                raise serializers.ValidationError({"标记设置错误": "PI单未付尾款不可选择此标签！"})

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["department"] = user.department

        validated_data["update_time"] = datetime.datetime.now()

        goods_details = validated_data.pop("goods_details", [])
        if goods_details:
            validated_data["currency"], validated_data["amount"], validated_data["quantity"] = self.check_goods_details(goods_details)
        if validated_data["sign"]:
            self.check_sign(instance, validated_data["sign"])
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        if goods_details:
            instance.ipogoods_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['ipo'] = instance
                _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
                goods_detail["goods_name"] = _q_goods
                goods_detail["goods_id"] = _q_goods.goods_id
                goods_detail["currency"] = validated_data["currency"]
                goods_detail["id"] = 'n'
                goods_detail.pop("xh")
                self.create_goods_detail(goods_detail)
        return instance


class EIPOGoodsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = EIPOGoods
        fields = "__all__"

    def get_eipo(self, instance):
        category_status = {
            1: "样机",
            2: "订单",
        }
        trade_modes = {
            1: "FOB",
            2: "CIF",
            3: "EXW",
            4: "DDP",
        }
        order_status = {
            0: "已取消",
            1: "待处理",
            2: "已完成",
        }
        try:
            ret = {
                "id": instance.eipo.id,
                "order_id": instance.eipo.order_id,
                "distributor": instance.eipo.distributor.name,
                "order_category": category_status.get(instance.eipo.order_category, None),
                "trade_mode": trade_modes.get(instance.eipo.trade_mode, None),
                "address": instance.eipo.address,
                "contract_id": instance.eipo.contract_id,
                "department": instance.eipo.department.name,
                "order_status": order_status.get(instance.eipo.order_status, None),
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_currency(self, instance):
        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未发货",
            2: "已发货",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(EIPOGoodsSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["eipo"] = self.get_eipo(instance)
        ret["currency"] = self.get_currency(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance





