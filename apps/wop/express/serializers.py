import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import ExpressWorkOrder


class ExpressWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ExpressWorkOrder
        fields = "__all__"

    def get_platform(self, instance):
        try:
            ret = {
                "id": instance.platform.id,
                "name": instance.platform.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

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

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "快递未递",
            2: "逆向未理",
            3: "正向未递",
            4: "快递在理",
            5: "复核未理",
            6: "终审未理",
            7: "财务审核",
            8: "工单完结",
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

    def get_process_tag(self, instance):
        process_tag = {
            0: "未分类",
            1: "待截单",
            2: "签复核",
            3: "改地址",
            4: "催派查",
            5: "丢件核",
            6: "纠纷中",
            7: "其他",
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
        category = {
            0: "截单退回",
            1: "无人收货",
            2: "客户拒签",
            3: "修改地址",
            4: "催件派送",
            5: "虚假签收",
            6: "丢件破损",
            7: "其他异常",
        }
        try:
            ret = {
                "id": instance.category,
                "name": category.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_wo_category(self, instance):
        wo_category = {
            0: "正向工单",
            1: "逆向工单",
        }
        try:
            ret = {
                "id": instance.wo_category,
                "name": wo_category.get(instance.wo_category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_mid_handler(self, instance):
        mid_handler = {
            0: "皮卡丘",
            1: "伊布",
            2: "可达鸭",
            3: "波比克",
        }
        try:
            ret = {
                "id": instance.mid_handler,
                "name": mid_handler.get(instance.mid_handler, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(ExpressWorkOrderSerializer, self).to_representation(instance)
        ret["company"] = self.get_company(instance)
        ret["category"] = self.get_category(instance)
        ret["wo_category"] = self.get_wo_category(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mid_handler"] = self.get_mid_handler(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


