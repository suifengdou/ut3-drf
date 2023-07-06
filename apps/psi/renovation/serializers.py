import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Renovation, RenovationGoods, Renovationdetail, LogRenovation, LogRenovationGoods, LogRenovationdetail
from apps.utils.logging.loggings import getlogs, logging
from apps.base.goods.models import Goods
from apps.psi.inbound.models import Inbound


class RenovationSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Renovation
        fields = "__all__"

    def get_mistake_tag(self, instance):
        process_tag = {
            0: "正常",
            1: "返回单号为空",
            2: "处理意见为空",
            3: "经销商反馈为空",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
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

    def to_representation(self, instance):
        ret = super(RenovationSerializer, self).to_representation(instance)
        ret["goods"] = self.get_goods(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        if "verification" not in validated_data:
            raise ValidationError({"创建错误": "没有验证号"})
        else:
            _q_inbound = Inbound.objects.filter(verification=validated_data["verification"])
            if _q_inbound.exists():
                inbound = _q_inbound[0]
                all_inbound_goods = inbound.inbounddetail_set.all()
                if len(all_inbound_goods) == 1:
                    inbound_goods = all_inbound_goods[0]
                    if inbound_goods.category != 2 or inbound_goods.valid_quantity == 0:
                        raise ValidationError({"创建错误": "关联多货品不存在或者类型非残品！"})
                else:
                    if "goods" not in validated_data:
                        raise ValidationError({"创建错误": "关联多货品入库单，货品项必填！"})
                    _q_inbound_goods = all_inbound_goods.filter(goods=validated_data["goods"])
                    if _q_inbound_goods.exists():
                        inbound_goods = _q_inbound_goods[0]
                    else:
                        raise ValidationError({"创建错误": "关联入库单未找到翻新货品！"})

        validated_data["order"] = inbound_goods
        validated_data["goods"] = inbound_goods.goods
        validated_data["warehouse"] = inbound_goods.warehouse
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogRenovation, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovation, "修改内容：%s" % str(content))
        return instance


class RenovationGoodsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = RenovationGoods
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

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "无货品不可审核",
            2: "保存出错",
            3: "仓库非法",
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
            0: "已取消",
            1: "未提交",
            2: "待审核",
            3: "已入账",
            4: "已清账"
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

    def get_category(self, instance):
        category_list = {
            1: "采购入库",
            2: "调拨入库",
            3: "退货入库",
            4: "生产入库",
            5: "保修入库",
            6: "其他入库",
            7: "残品入库"
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.inbounddetail_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "goods": {
                    "id": goods_detail.goods.id,
                    "name": goods_detail.goods.name
                },
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memo": goods_detail.memo
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(RenovationGoodsSerializer, self).to_representation(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["category"] = self.get_category(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogRenovationGoods, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovationGoods, "修改内容：%s" % str(content))
        return instance


class RenovationdetailSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Renovationdetail
        fields = "__all__"

    def get_order(self, instance):
        category_list = {
            1: "采购入库",
            2: "调拨入库",
            3: "退货入库",
            4: "生产入库",
            5: "保修入库",
            6: "其他入库"
        }
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.code,
                "category": category_list.get(instance.order.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
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

    def get_category(self, instance):
        category_list = {
            1: "正品",
            2: "残品",
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未提交",
            2: "待审核",
            3: "已入账",
            4: "已清账"
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(RenovationdetailSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["category"] = self.get_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogRenovationdetail, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovationdetail, "修改内容：%s" % str(content))
        return instance











