import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import StorageWorkOrder


class StorageWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = StorageWorkOrder
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
            1: "逆向未递",
            2: "逆向未理",
            3: "正向未递",
            4: "仓储未理",
            5: "复核未理",
            6: "财务审核",
            7: "工单完结",
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
        category = {
            0: "入库错误",
            1: "系统问题",
            2: "单据问题",
            3: "订单类别",
            4: "入库咨询",
            5: "出库咨询",
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


    def to_representation(self, instance):
        ret = super(StorageWorkOrderSerializer, self).to_representation(instance)
        ret["company"] = self.get_company(instance)
        ret["category"] = self.get_category(instance)
        ret["wo_category"] = self.get_wo_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


