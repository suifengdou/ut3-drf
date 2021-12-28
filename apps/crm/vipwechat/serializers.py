import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Specialist, VIPWechat


class SpecialistSerializer(serializers.ModelSerializer):

    class Meta:
        model = Specialist
        fields = "__all__"

    def get_username(self, instance):
        try:
            ret = {
                "id": instance.username.id,
                "name": instance.username.username
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(SpecialistSerializer, self).to_representation(instance)
        ret["username"] = self.get_username(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        all_specialist = user.specialist_set.all().filter(is_default=True)
        if all_specialist.exists():
            if validated_data["is_default"]:
                raise serializers.ValidationError({"错误": "一个账号只可存在一个默认服务账号！"})
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        user = self.context["request"].user
        all_specialist = user.specialist_set.all().filter(is_default=True)
        if all_specialist.exists():
            if validated_data["is_default"]:
                raise serializers.ValidationError({"错误": "一个账号只可存在一个默认服务账号！"})
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class VIPWechatSerializer(serializers.ModelSerializer):
    class Meta:
        model = VIPWechat
        fields = "__all__"

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_specialist(self, instance):
        try:
            ret = {
                "id": instance.specialist.id,
                "name": instance.specialist.name
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
            1: "等待确认",
            2: "确认完成",
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
        ret = super(VIPWechatSerializer, self).to_representation(instance)
        ret["customer"] = self.get_customer(instance)
        ret["specialist"] = self.get_specialist(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


