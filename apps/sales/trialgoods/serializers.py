import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import RefundManualOrder, RMOGoods, Renovate, RenovateGoods, Renovatedetail, LogRenovate, LogRenovatedetail, LogRenovateGoods, LogRefundManualOrder, LogRMOGoods
from apps.base.goods.models import Goods
from apps.utils.geography.tools import PickOutAdress
from apps.utils.logging.loggings import logging


class RefundManualOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = RefundManualOrder
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
        ret = super(RefundManualOrderSerializer, self).to_representation(instance)
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
            goods_detail = RMOGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = RMOGoods.objects.filter(id=data["id"]).update(**data)
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
        logging(order, user, LogRefundManualOrder, "手工创建")
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
        logging(instance, user, LogRefundManualOrder, "修改内容：%s" % str(content))
        return instance
