from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Shop, Platform


class ShopSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Shop
        fields = "__all__"

    def get_platform(self, instance):
        ret = {
            "id": instance.platform.id,
            "name": instance.platform.name
        }
        return ret

    def get_company(self, instance):
        ret = {
            "id": instance.company.id,
            "name": instance.company.name
        }
        return ret

    def to_representation(self, instance):
        ret = super(ShopSerializer, self).to_representation(instance)
        try:
            ret["platform"] = self.get_platform(instance)
            ret["company"] = self.get_company(instance)
        except:
            error = { "id": -1, "name": "显示错误"}
            ret["platform"] = error
            ret["company"] = error
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class PlatformSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间",
                                            help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间",
                                            help_text="更新时间")

    class Meta:
        model = Platform
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(PlatformSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance