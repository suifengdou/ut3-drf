import datetime, re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CSGoods, LogCSGoods
from apps.crm.labels.models import Label
from apps.utils.logging.loggings import logging
from apps.crm.customerlabel.views import QueryLabel, CreateLabel, DeleteLabel, RecoverLabel
from apps.crm.customers.models import Customer, LogCustomer


class CSGoodsSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(required=False)
    smartphone = serializers.JSONField(required=False)

    class Meta:
        model = CSGoods
        fields = "__all__"

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(CSGoodsSerializer, self).to_representation(instance)
        ret["customer"] = self.get_customer(instance)
        ret["goods"] = self.get_goods(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        if 'smartphone' in validated_data:
            smartphone = validated_data.pop("smartphone", None)
            if not re.match(r"^1[23456789]\d{9}$", smartphone):
                raise ValidationError({"创建错误": "用户电话错误！"})
        else:
            raise ValidationError({"创建错误": "无用户联系电话！"})

        _q_customer = Customer.objects.filter(name=smartphone)
        if _q_customer.exists():
            customer = _q_customer[0]
        else:
            customer_dict = {"name": smartphone}
            try:
                customer = Customer.objects.create(**customer_dict)
                logging(customer, user, LogCustomer, "由客户货品模块创建")
            except Exception as e:
                raise ValidationError({"创建错误": f"新用户创建错误：{e}！"})
        validated_data["customer"] = customer

        if 'sn' in validated_data:
            if not re.match("[A-Z]{3}\d{7}[A-Z]{1}\d{5}|\d{8}|\d{4}[A-Z]{3}\d{3}[A-Z]{1}\d{5}", str(validated_data['sn'])):
                raise ValidationError({"创建错误": "SN错误"})
        else:
            raise ValidationError({"创建错误": "SN是必填项"})
        if 'purchase_time' not in validated_data:
            raise ValidationError({"创建错误": "购买时间是必填项"})
        if 'goods' not in validated_data:
            raise ValidationError({"创建错误": "整机是必填项"})

        _q_check_address = self.Meta.model.objects.filter(sn=validated_data['sn'], customer=customer)
        if _q_check_address.exists():
            raise ValidationError({"创建错误": "已存在此客户地址不能重复创建！"})

        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCSGoods, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCSGoods, "修改内容：%s" % str(content))
        return instance




