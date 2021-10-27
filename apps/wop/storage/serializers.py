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
            1: "工单待递",
            2: "工单待理",
            3: "工单待定",
            4: "财务审核",
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

    def get_category(self, instance):
        category_list = {
            1: "常规工作",
            2: "入库问题",
            3: "出库问题",
            4: "单据问题",
            5: "工厂问题",
            6: "快递问题",
            7: "信息咨询",
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
            1: "关键字重复",

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

    def get_handling_status(self, instance):
        handling_list = {
            0: "未处理",
            1: "已处理",
        }
        try:
            ret = {
                "id": instance.handling_status,
                "name": handling_list.get(instance.handling_status, None)
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
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["handling_status"] = self.get_handling_status(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        validated_data["is_forward"] = user.is_our
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


