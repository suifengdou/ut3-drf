import datetime
import jieba
import re
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import ManualOrder, MOGoods, ManualOrderExport, LogManualOrder, LogManualOrderExport
from apps.base.goods.models import Goods
from apps.utils.geography.models import District
from apps.utils.geography.tools import PickOutAdress
from apps.utils.logging.loggings import logging


class ManualOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = ManualOrder
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
            4: "试用体验",
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
            10: "输出单保存出错",
            11: "货品数量错误",
            12: "无收件人",
            13: "此类型不可发整机"
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

    def get_assign_express(self, instance):
        EXPRESS_LIST = {
            0: "随机",
            1: "顺丰",
            2: "圆通",
            3: "韵达",
        }
        try:
            ret = {
                "id": instance.assign_express,
                "name": EXPRESS_LIST.get(instance.assign_express, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_settle_category(self, instance):
        settle_category = {
            0: "常规",
            1: "试用退回",
            2: "OA报损",
            3: "退回苏州",
            4: "试用销售",
        }
        try:
            ret = {
                "id": instance.settle_category,
                "name": settle_category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.mogoods_set.all()
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
        ret = super(ManualOrderSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["department"] = self.get_department(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["assign_express"] = self.get_assign_express(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["settle_category"] = self.get_settle_category(instance)
        ret["warehouse"] = self.get_warehouse(instance)
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
            goods_detail = MOGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = MOGoods.objects.filter(id=data["id"]).update(**data)
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

        manual_order = self.Meta.model.objects.create(**validated_data)
        logging(manual_order, user, LogManualOrder, "手工创建")
        for goods_detail in goods_details:
            goods_detail['manual_order'] = manual_order
            goods_name = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = goods_name
            goods_detail["goods_id"] = goods_name.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        return manual_order

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
        logging(instance, user, LogManualOrder, "修改内容：%s" % str(content))
        return instance


class MOGoodsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = MOGoods
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
                "department": instance.manual_order.department.name,
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
            4: "试用中",
            5: "已完结",
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
        ret = super(MOGoodsSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["manual_order"] = self.get_manual_order(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ManualOrderExportSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ManualOrderExport
        fields = "__all__"

    def get_ori_order(self, instance):
        try:
            ret = {
                "id": instance.ori_order.id,
                "name": instance.ori_order.order_id,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name,
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

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理"
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
        SIGN_LIST = {
            0: "无",
            1: "先不发货",
            2: "等待核实",
            3: "锁定快递",
            4: "已送礼品",
            5: "大菜鸟仓",
            6: "核实退款",
            7: "库房无货",
            8: "专项审核",
            9: "替换货品"
        }
        try:
            ret = {
                "id": instance.sign,
                "name": SIGN_LIST.get(instance.sign, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(ManualOrderExportSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["ori_order"] = self.get_ori_order(instance)
        ret["sign"] = self.get_sign(instance)
        return ret




