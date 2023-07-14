import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import OriInbound, Inbound, InboundDetail, LogOriInbound, LogInboundDetail, LogInbound
from apps.utils.logging.loggings import getlogs, logging
from apps.base.goods.models import Goods


class OriInboundSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriInbound
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

    def to_representation(self, instance):
        ret = super(OriInboundSerializer, self).to_representation(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class InboundSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = Inbound
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
        ret = super(InboundSerializer, self).to_representation(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["category"] = self.get_category(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret

    def create_goods_detail(self, data):
        user = self.context["request"].user
        data["creator"] = user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = InboundDetail.objects.create(**data)
            goods_detail.code = f'{goods_detail.code}-{goods_detail.id}'
            logging(goods_detail, user, LogInboundDetail, "创建")

        else:
            goods_detail = InboundDetail.objects.filter(id=data["id"]).update(**data)
            logging(goods_detail, user, LogInboundDetail, "更新")
        return goods_detail

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称和数量为必填项！")
        goods_list = list(map(lambda x: x["goods"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        if "verification" not in validated_data:
            raise ValidationError({"创建错误": "没有验证号"})
        else:
            _q_order = self.Meta.model.objects.filter(verification=validated_data["verification"])
            if _q_order.exists():
                raise ValidationError({"创建错误": "验证号不可以重复"})
        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)
        validated_data["code"] = validated_data["code"].replace("-", "")
        order = self.Meta.model.objects.create(**validated_data)
        order.code = f'{order.code}-{order.id}'
        order.save()
        logging(order, user, LogInbound, "手工创建")
        for goods_detail in goods_details:
            goods_detail['order'] = order
            goods_detail['code'] = order.code
            goods_detail['warehouse'] = order.warehouse
            goods_detail["goods"] = Goods.objects.filter(id=goods_detail["goods"])[0]
            goods_detail.pop("xh")
            if order.category in [3, 7]:
                goods_detail["category"] = 2
            self.create_goods_detail(goods_detail)
        return order

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()

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
            instance.inbounddetail_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['order'] = instance
                goods_detail['code'] = instance.code
                _q_goods = Goods.objects.filter(id=goods_detail["goods"])[0]
                goods_detail["goods"] = _q_goods
                goods_detail['warehouse'] = instance.warehouse
                goods_detail['id'] = "n"
                goods_detail.pop("xh")
                if validated_data["category"] in [3, 7]:
                    goods_detail["category"] = 2
                self.create_goods_detail(goods_detail)
                content.append('更新货品：%s x %s' % (_q_goods.name, goods_detail["quantity"]))
        logging(instance, user, LogInbound, "修改内容：%s" % str(content))
        return instance


class InboundDetailSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = InboundDetail
        fields = "__all__"

    def get_order(self, instance):
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
        ret = super(InboundDetailSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["category"] = self.get_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance













