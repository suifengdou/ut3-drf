import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Goods, GoodsCategory


class GoodsSerializer(serializers.ModelSerializer):
    CATEGORY = (
        (0, "整机"),
        (1, "配件"),
        (2, "礼品"),
    )

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Goods
        fields = "__all__"

    def get_category(self, instance):
        try:
            ret = {
                "id": instance.category.id,
                "name": instance.category.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods_attribute(self, instance):
        goods_attribute = {
            0: "整机",
            1: "配件",
            2: "礼品",
        }
        try:
            ret = {
                "id": instance.goods_attribute,
                "name": goods_attribute.get(instance.goods_attribute, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(GoodsSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["goods_attribute"] = self.get_goods_attribute(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class GoodsCategorySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = GoodsCategory
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(GoodsCategorySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance