import datetime
import json
from functools import reduce

from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
from .models import OriTailOrder, OTOGoods, TailOrder, TOGoods, RefundOrder, ROGoods, PayBillOrder, PBOGoods, \
    ArrearsBillOrder, ABOGoods, FinalStatement, FinalStatementGoods, AccountInfo, PBillToAccount, ABillToAccount,  TailToExpense, RefundToPrestore
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress


class OriTailOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = OriTailOrder
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "申请未报",
            2: "正在审核",
            3: "单据生成",
            4: "发货完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '待核实',
            2: '已确认',
            3: '待清账',
            4: '已处理',
            5: '驳回',
            6: '物流订单',
            7: '部分发货',
            8: '重损发货',
            9: '非重损发货',
            10: '特殊发货',
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
            1: "账号未设置公司",
            2: "货品金额是零",
            3: "收件人手机错误",
            4: "单号不符合规则",
            5: "需要选择拆单发货",
            6: "递交订单出错",
            7: "生成订单货品出错",
            8: "货品数量错误",
            9: "重复生成订单，联系管理员",
            10: "重复生成订单，联系管理员",
            11: "生成订单货品出错，联系管理员",
            12: "发货仓库和单据类型不符",
            13: "订单货品导入出错",
            14: "导入货品编码错误",
            15: "重复订单",
            16: "型号错误",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
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

    def get_order_category(self, instance):
        order_category = {
            1: "销售订单",
            2: "售后换货",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": order_category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mode_warehouse(self, instance):
        mode_warehouse = {
            0: "回流",
            1: "二手",

        }
        try:
            ret = {
                "id": instance.mode_warehouse,
                "name": mode_warehouse.get(instance.mode_warehouse, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sent_city(self, instance):
        try:
            ret = {
                "id": instance.sent_city.id,
                "name": instance.sent_city.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.otogoods_set.all()
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
        ret = super(OriTailOrderSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["mode_warehouse"] = self.get_mode_warehouse(instance)
        ret["sent_city"] = self.get_sent_city(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

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
            amount_list = list(map(lambda x: int(x["price"]) * int(x["quantity"]), goods_details))
            quantity_list = list(map(lambda x: int(x["quantity"]), goods_details))
            amount = reduce(lambda x, y: x + y, amount_list)
            quantity = reduce(lambda x, y: x + y, quantity_list)
            return amount, quantity

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = OTOGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = OTOGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        goods_details = validated_data.pop("goods_details", [])
        amount, quantity = self.check_goods_details(goods_details)
        validated_data["amount"] = amount
        validated_data["quantity"] = quantity
        if self.context["request"].user.department:

            validated_data["sign_department"] = self.context["request"].user.department
        else:
            raise serializers.ValidationError("登陆账号没有设置部门，不可以创建！")
        if validated_data["shop"].company:
            if validated_data["shop"].company.category == 4:
                validated_data["sign_company"] = validated_data["shop"].company
            else:
                raise serializers.ValidationError("店铺设置公司，不是经销代理，不可以创建！")
        else:
            raise serializers.ValidationError("店铺没有设置公司，不可以创建！")

        address = validated_data.get("sent_address", None)
        if address:
            _spilt_addr = PickOutAdress(address)
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            validated_data["sent_city"] = _rt_addr["city"]
            if _rt_addr["district"]:
                validated_data["sent_district"] = _rt_addr["district"].name
        else:
            raise serializers.ValidationError("无法获取地址！")

        ori_tail_order = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail['ori_tail_order'] = ori_tail_order
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return ori_tail_order

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        goods_details = validated_data.pop("goods_details", [])
        amount, quantity = self.check_goods_details(goods_details)
        validated_data["amount"] = amount
        validated_data["quantity"] = quantity
        create_time = validated_data.pop("create_time", "")
        update_tim = validated_data.pop("update_tim", "")
        address = validated_data.get("sent_address", None)
        if address:
            _spilt_addr = PickOutAdress(address)
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            validated_data["sent_city"] = _rt_addr["city"]
            if _rt_addr["district"]:
                validated_data["sent_district"] = _rt_addr["district"].name

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        for goods_detail in goods_details:
            goods_detail['ori_tail_order'] = instance
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return instance


class OTOGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OTOGoods
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(OTOGoodsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class TailOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = TailOrder
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "发货处理",
            2: "发货完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '待核实',
            2: '已确认',
            3: '部分发货',
            4: '已处理',
            5: '驳回',
            6: '物流订单',
            7: '部分发货',
            8: '重损发货',
            9: '非重损发货',
            10: '特殊发货',
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
            1: "快递单号错误",
            2: "生成对账单出错",
            3: "货品明细未发货",
            4: "结算单货品保存出错",
            5: "支出单生成错误",
            6: "支出流水成错误",
            7: "支出划账错误",
            8: "尾货对账单重复",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
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

    def get_order_category(self, instance):
        order_category = {
            1: "销售订单",
            2: "售后换货",

        }
        try:
            ret = {
                "id": instance.order_category,
                "name": order_category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mode_warehouse(self, instance):
        mode_warehouse = {
            0: "回流",
            1: "二手",

        }
        try:
            ret = {
                "id": instance.mode_warehouse,
                "name": mode_warehouse.get(instance.mode_warehouse, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sent_city(self, instance):
        try:
            ret = {
                "id": instance.sent_city.id,
                "name": instance.sent_city.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.togoods_set.all()
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
                "settlement_price": goods_detail.settlement_price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret


    def to_representation(self, instance):
        ret = super(TailOrderSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["mode_warehouse"] = self.get_mode_warehouse(instance)
        ret["sent_city"] = self.get_sent_city(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class TOGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = TOGoods
        fields = "__all__"

    def get_shop(self, shop):

        try:
            ret = {
                "id": shop.id,
                "name": shop.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sent_city(self, sent_city):

        try:
            ret = {
                "id": sent_city.id,
                "name": sent_city.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sent_province(self, sent_province):
        try:
            ret = {
                "id": sent_province.id,
                "name": sent_province.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(TOGoodsSerializer, self).to_representation(instance)
        fields_str = ['order_id', 'sent_consignee', 'sent_consignee', 'sent_address', 'sent_smartphone', 'message',
                      'sent_district', 'mode_warehouse', 'sent_province', 'sent_city', 'shop']
        for key in fields_str:
            ret[key] = getattr(instance.tail_order, key, None)

        ret["shop"] = self.get_shop(ret["shop"])
        ret["sent_city"] = self.get_sent_city(ret["sent_city"])
        ret["sent_province"] = self.get_sent_province(ret["sent_province"])
        ret["deliver_condition"] = "款到发货"
        ret["discounts"] = 0
        ret["post_fee"] = 0
        ret["order_category"] = "线下零售"
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class RefundOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)
    t_order_status = serializers.JSONField(required=False)

    class Meta:
        model = RefundOrder
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待递交",
            2: "待处理",
            3: "已审核",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = { "id": -1, "name": "错误" }
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '待核实',
            2: '已确认',
            3: '待清账',
            4: '已处理',
            5: '部分到货',
            6: '已到货',
            7: '部分发货',
            8: '换货',
            9: '驳回',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: '正常',
            1: '退换数量超出原单数量',
            2: '退换金额超出原单金额',
            3: '无退货原因',
            4: '无返回快递单号',
            5: '已存在关联入库，不可以驳回',
            6: '非换货单不可以标记',
            7: '非已到货状态不可以审核',
            8: '退换数量和收货数量不一致',
            9: '退换金额和收货金额不一致',
            10: '关联预存单出错',
            11: '当前登录人无预存账户',
            12: '创建预存单错误',
            13: '关联的订单未发货',
            14: '不是退货单不可以审核',
            15: '物流单号重复',
            16: '入库单已经操作，不可以清除标记',
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_order_category(self, instance):
        order_category = {
            3: "退-退货退款",
            4: "退-换货退回",
            5: "退-仅退款",

        }
        try:
            ret = {
                "id": instance.order_category,
                "name": order_category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mode_warehouse(self, instance):
        mode_warehouse = {
            0: "回流",
            1: "二手",

        }
        try:
            ret = {
                "id": instance.mode_warehouse,
                "name": mode_warehouse.get(instance.mode_warehouse, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_sent_city(self, instance):
        try:
            ret = {
                "id": instance.sent_city.id,
                "name": instance.sent_city.name,
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_tail_order(self, instance):
        try:
            ret = {
                "id": instance.tail_order.id,
                "name": instance.tail_order.order_id
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.rogoods_set.all()
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
                "settlement_price": goods_detail.settlement_price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(RefundOrderSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["mode_warehouse"] = self.get_mode_warehouse(instance)
        ret["sent_city"] = self.get_sent_city(instance)
        ret["tail_order"] = self.get_tail_order(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def to_internal_value(self, data):
        return super(RefundOrderSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        validated_data.pop("goods_details", None)
        fields_list_str = ['sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address', 'mode_warehouse',
                           "shop", 'sent_city', 'sign_company', 'sign_department']
        fields_list_obj = []
        tail_order = validated_data["tail_order"]
        for key in fields_list_str:
            validated_data[key] = getattr(tail_order, key, None)
        try:
            for attr in fields_list_obj:
                value = getattr(tail_order, attr, None)
                validated_data[attr] = value.id
        except:
            validated_data[key] = ''
        validated_data["shop"] = tail_order.shop
        validated_data["order_id"] = "RO" + tail_order.order_id
        goods_details = tail_order.togoods_set.all()
        _ret_goods_details = []
        for goods_detail in goods_details:
            goods = {
                "id": "n",
                "goods_id": goods_detail.goods_id,
                "goods_name": goods_detail.goods_name,
                "goods_nickname": goods_detail.goods_nickname,
                "quantity": goods_detail.quantity,
                "settlement_price": goods_detail.settlement_price,
                "settlement_amount": goods_detail.settlement_amount,
                "memorandum": goods_detail.memorandum
            }
            _ret_goods_details.append(goods)
        goods_details = _ret_goods_details
        validated_data["creator"] = self.context["request"].user.username
        amount, quantity = self.check_goods_details(goods_details)
        validated_data["amount"] = amount
        validated_data["ori_amount"] = amount
        validated_data["quantity"] = quantity
        if not self.context["request"].user.company or not self.context["request"].user.company:
            raise serializers.ValidationError("登陆账号没有设置公司或者部门，不可以创建！")
        refund_order = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail["refund_order"] = refund_order
            goods_detail.pop("xh", None)
            self.create_goods_detail(goods_detail)

        return refund_order

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        goods_details = validated_data.pop("goods_details", [])
        amount, quantity = self.check_goods_details(goods_details)
        validated_data["amount"] = amount
        validated_data["quantity"] = quantity
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        for goods_detail in goods_details:
            goods_detail["refund_order"] = instance
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return instance

    def check_goods_details(self, goods_details):
        if not goods_details:
            return 0
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("settlement_price", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")
        else:
            amount_list = list(map(lambda x: float(x["settlement_price"]) * float(x["quantity"]), goods_details))
            quantity_list = list(map(lambda x: int(x["quantity"]), goods_details))
            amount = reduce(lambda x, y: round(x + y, 2), amount_list)
            quantity = reduce(lambda x, y: x + y, quantity_list)
            return amount, quantity

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = ROGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = ROGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail


class ROGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ROGoods
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待递交",
            2: "待入库",
            3: "部分到货",
            4: "已到货",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = { "id": -1, "name": "错误" }
        return ret

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '待处理',
            2: '已确认',
            3: '待清账',
            4: '已处理',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: '正常',
            1: '入库数量是0',
            2: '入库数和待收货数不符',
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name,
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mode_warehouse(self, instance):
        mode_warehouse = {
            0: "回流",
            1: "二手",

        }
        try:
            ret = {
                "id": instance.refund_order.mode_warehouse,
                "name": mode_warehouse.get(instance.refund_order.mode_warehouse, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_refund_order(self, instance):
        try:
            ret = {
                "id": instance.refund_order.id,
                "name": instance.refund_order.order_id,
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_track_no(self, instance):
        try:
            ret = instance.refund_order.track_no
        except:
            ret = "错误"
        return ret

    def get_sent_consignee(self, instance):
        try:
            ret = instance.refund_order.sent_consignee
        except:
            ret = "错误"
        return ret

    def get_sent_smartphone(self, instance):
        try:
            ret = instance.refund_order.sent_smartphone
        except:
            ret = "错误"
        return ret

    def to_representation(self, instance):
        ret = super(ROGoodsSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["mode_warehouse"] = self.get_mode_warehouse(instance)
        ret["refund_order"] = self.get_refund_order(instance)
        ret["track_no"] = self.get_track_no(instance)
        ret["sent_consignee"] = self.get_sent_consignee(instance)
        ret["sent_smartphone"] = self.get_sent_smartphone(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class PayBillOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = PayBillOrder
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(PayBillOrderSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class PBOGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = PBOGoods
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(PBOGoodsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ArrearsBillOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ArrearsBillOrder
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(ArrearsBillOrderSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ABOGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ABOGoods
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(ABOGoodsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class FinalStatementSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = FinalStatement
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(FinalStatementSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class FinalStatementGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = FinalStatementGoods
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(FinalStatementGoodsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class AccountInfoSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = AccountInfo
        fields = "__all__"

    def get_process_tag(self, instance):
        process = {
            0: '未处理',
            1: '待核实',
            2: '已确认',
            3: '待清账',
            4: '已处理',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process.get(instance.process_tag, None)
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

    def get_sign_company(self, instance):
        try:
            ret = {
                "id": instance.sign_company.id,
                "name": instance.sign_company.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_category(self, instance):
        order_category = {
            1: "销售订单",
            2: "售后换货",
            3: "退-退货退款",
            4: "退-换货退回",
            5: "退-仅退款",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": order_category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mode_warehouse(self, instance):
        mode_warehouse = {
            0: "回流",
            1: "二手",

        }
        try:
            ret = {
                "id": instance.mode_warehouse,
                "name": mode_warehouse.get(instance.mode_warehouse, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(AccountInfoSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["sign_company"] = self.get_sign_company(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["mode_warehouse"] = self.get_mode_warehouse(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class PBillToAccountSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = PBillToAccount
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(PBillToAccountSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ABillToAccountSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ABillToAccount
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(ABillToAccountSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class TailToExpenseSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = TailToExpense
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(TailToExpenseSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class RefundToPrestoreSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = RefundToPrestore
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(RefundToPrestoreSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance