import datetime
from rest_framework import serializers
from django.db.models import Avg,Sum,Max,Min
from rest_framework.exceptions import ValidationError
from .models import Inventory
from apps.psi.inbound.models import InboundDetail


class InventorySerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Inventory
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

    def get_balance(self, instance):
        try:
            balance = InboundDetail.objects.filter(goods=instance.goods_name, warehouse=instance.warehouse, category=1).aggregate(Sum("valid_quantity"))["valid_quantity__sum"]
            if not balance:
                balance = 0
        except Exception as e:
            balance = 0
        return balance

    def get_frozeed(self, instance):
        try:
            frozeed = InboundDetail.objects.filter(goods=instance.goods_name, warehouse=instance.warehouse).aggregate(Sum("froze_quantity"))["froze_quantity__sum"]
            if not frozeed:
                frozeed = 0
        except Exception as e:
            frozeed = 0
        return frozeed

    def get_broken(self, instance):
        try:
            broken = InboundDetail.objects.filter(goods=instance.goods_name, warehouse=instance.warehouse, category=2).aggregate(Sum("valid_quantity"))["valid_quantity__sum"]
            if not broken:
                broken = 0
        except Exception as e:
            balance = 0
        return broken

    def to_representation(self, instance):
        ret = super(InventorySerializer, self).to_representation(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["balance"] = self.get_balance(instance)
        ret["frozeed"] = self.get_frozeed(instance)
        ret["broken"] = self.get_broken(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


