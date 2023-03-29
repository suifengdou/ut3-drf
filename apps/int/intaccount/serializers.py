import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Currency, IntAccount


class CurrencySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Currency
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CurrencySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class IntAccountSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = IntAccount
        fields = "__all__"

    def get_currency(self, instance):
        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name
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

    def to_representation(self, instance):
        ret = super(IntAccountSerializer, self).to_representation(instance)
        ret["currency"] = self.get_currency(instance)
        ret["company"] = self.get_company(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance










