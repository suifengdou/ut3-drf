import datetime
import jieba
import re
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import DealerParts, DPGoods
from apps.base.goods.models import Goods
from apps.utils.geography.models import District
from apps.utils.geography.tools import PickOutAdress
from apps.base.shop.models import Shop


class DealerPartsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = DealerParts
        fields = "__all__"

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_province(self, instance):
        try:
            ret = {
                "id": instance.province.id,
                "name": instance.province.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.district.id,
                "name": instance.district.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_department(self, instance):
        try:
            ret = {
                "id": instance.department.id,
                "name": instance.department.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_category(self, instance):
        category = {
            1: "质量问题",
            2: "开箱即损",
            3: "礼品赠品",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未处理",
            2: "已处理",
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
            1: "重复递交",
            2: "售后配件需要补全sn、部件和描述",
            3: "无部门",
            4: "省市区出错",
            5: "手机错误",
            6: "无店铺",
            7: "集运仓地址",
            8: "14天内重复",
            9: "14天外重复",
            10: "手工单保存出错",
            11: "手工单货品保存出错"
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

    def get_goods_details(self, instance):
        goods_details = instance.dpgoods_set.all()
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
        ret = super(DealerPartsSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["department"] = self.get_department(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["order_status"] = self.get_order_status(instance)
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

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            data.pop("name", None)
            goods_detail = DPGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = DPGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):

        user = self.context["request"].user
        validated_data["creator"] = user.username
        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)
        validated_data["department"] = user.department
        _q_shop = user.company.shop_set.all()
        if _q_shop.exists():
            validated_data["shop"] = _q_shop[0]
        else:
            validated_data["shop"] = Shop.objects.filter(name="旗舰店供应商")[0]

        _spilt_addr = PickOutAdress(validated_data["address"])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        cs_info_fields = ["province", "city", "district", "address"]
        for key_word in cs_info_fields:
            validated_data[key_word] = _rt_addr.get(key_word, None)

        if '集运' in str(validated_data["address"]):
            raise serializers.ValidationError("地址是集运仓")

        dealer_parts = self.Meta.model.objects.create(**validated_data)
        for goods_detail in goods_details:
            goods_detail['dealer_parts'] = dealer_parts
            goods_name = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = goods_name
            goods_detail["goods_id"] = goods_name.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return dealer_parts

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["department"] = user.department

        validated_data["update_time"] = datetime.datetime.now()

        _spilt_addr = PickOutAdress(validated_data["address"])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        cs_info_fields = ["province", "city", "district", "address"]
        for key_word in cs_info_fields:
            validated_data[key_word] = _rt_addr.get(key_word, None)

        if '集运' in str(validated_data["address"]):
            raise serializers.ValidationError("地址是集运仓")

        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        instance.mogoods_set.all().delete()
        for goods_detail in goods_details:
            goods_detail['manual_order'] = instance
            _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = _q_goods
            goods_detail["goods_id"] = _q_goods.goods_id
            goods_detail["id"] = 'n'
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return instance


class DPGoodsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DPGoods
        fields = "__all__"

    def get_manual_order(self, instance):
        category_status = {
            1: "质量问题",
            2: "开箱即损",
            3: "礼品赠品",
        }
        try:
            ret = {
                "id": instance.manual_order.id,
                "erp_order_id": instance.manual_order.erp_order_id,
                "shop": instance.manual_order.shop.name,
                "nickname": instance.manual_order.nickname,
                "receiver": instance.manual_order.receiver,
                "address": instance.manual_order.address,
                "mobile": instance.manual_order.mobile,
                "order_id": instance.manual_order.order_id,
                "order_category": category_status.get(instance.manual_order.order_category, None),
                "m_sn": instance.manual_order.m_sn,
                "broken_part": instance.manual_order.broken_part,
                "description": instance.manual_order.description
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
            1: "未处理",
            2: "已导入",
            3: "已发货",
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
        ret = super(DPGoodsSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["manual_order"] = self.get_manual_order(instance)
        return ret

    def create(self, validated_data):
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance






