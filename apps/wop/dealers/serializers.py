import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import DealerWorkOrder


class DealerWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DealerWorkOrder
        fields = "__all__"

    def get_company(self, instance):
        try:
            ret = {
                "id": instance.company.id,
                "name": instance.company.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_process_tag(self, instance):
        process_tag = {
            0: '未处理',
            1: '已处理',
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

    def get_category(self, instance):
        category_list = {
            1: '退货',
            2: '换货',
            3: '维修',
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

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "返回单号或快递为空",
            2: "处理意见为空",
            3: "执行内容为空",
            4: "驳回原因为空",
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
            1: "等待递交",
            2: "等待处理",
            3: "等待执行",
            4: "等待确认",
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
        ret = super(DealerWorkOrderSerializer, self).to_representation(instance)
        ret["company"] = self.get_company(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["category"] = self.get_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def to_internal_value(self, data):
        return super(DealerWorkOrderSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        if not validated_data.get("category", None):
            raise serializers.ValidationError({"category": "单据类型是必填项！"})
        user = self.context["request"].user
        validated_data["creator"] = user.username
        validated_data["company"] = user.company
        _q_dealer_order = self.Meta.model.objects.filter(order_id=validated_data["order_id"])
        if _q_dealer_order.exists():
            raise serializers.ValidationError({"order_id": "相同单号只可创建一次工单！！"})
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


