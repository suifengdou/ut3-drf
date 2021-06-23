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


    def to_representation(self, instance):
        ret = super(GoodsSerializer, self).to_representation(instance)
        try:
            ret["category"] = GoodsCategory.objects.filter(id=ret["category"])[0].name
            ret["goods_attribute"] = self.__class__.CATEGORY[ret["goods_attribute"]][1]
        except:
            ret["category"] = "类别错误"
            ret["goods_attribute"] = "属性错误"
        print(ret)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class GoodsCategorySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = GoodsCategory
        fields = ["id", "name", "code", "create_time", "update_time", "is_delete", "creator"]


    def to_representation(self, instance):
        ret = super(GoodsCategorySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance