import datetime, re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CSAddress, LogCSAddress
from apps.crm.labels.models import Label
from apps.utils.logging.loggings import logging
from apps.crm.customerlabel.views import QueryLabel, CreateLabel, DeleteLabel, RecoverLabel
from apps.crm.customers.models import Customer, LogCustomer
from apps.utils.geography.tools import PickOutAdress


class CSAddressSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(required=False)
    city = serializers.CharField(required=False)

    class Meta:
        model = CSAddress
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

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name,
                "province": instance.city.province.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(CSAddressSerializer, self).to_representation(instance)
        ret["customer"] = self.get_customer(instance)
        ret["city"] = self.get_city(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        if 'mobile' in validated_data:
            if not re.match(r"^1[23456789]\d{9}$", validated_data["mobile"]):
                raise ValidationError({"创建错误": "用户电话错误！"})
        else:
            raise ValidationError({"创建错误": "无用户联系电话！"})
        _q_customer = Customer.objects.filter(name=validated_data["mobile"])
        if _q_customer.exists():
            customer = _q_customer[0]
        else:
            customer_dict = {"name": validated_data["mobile"]}
            try:
                customer = Customer.objects.create(**customer_dict)
                logging(customer, user, LogCustomer, "由客户地址模块创建")
            except Exception as e:
                raise ValidationError({"创建错误": f"新用户创建错误：{e}！"})
        validated_data["customer"] = customer

        validated_data["address"] = re.sub("[!$%&\'*+,./:：;<=>?，。?★、…【】《》？（）() “”‘’！[\\]^_`{|}~\s]+", "",
                                           str(validated_data["address"]))

        if validated_data["address"]:
            _spilt_addr = PickOutAdress(validated_data["address"])
            _rt_addr = _spilt_addr.pickout_addr()

            if not isinstance(_rt_addr, dict):
                raise ValidationError({"创建错误": "地址无法提取省市区"})
            validated_data["city"] = _rt_addr["city"]
        else:
            raise ValidationError({"创建错误": "无法获取地址！"})

        _q_check_address = self.Meta.model.objects.filter(customer=validated_data["customer"],
                                                          name=validated_data["name"],
                                                          mobile=validated_data["mobile"],
                                                          address=validated_data["address"])
        if _q_check_address.exists():
            raise ValidationError({"创建错误": "已存在此客户地址不能重复创建！"})

        _q_default_address = self.Meta.model.objects.filter(customer=customer, is_default=True)
        if _q_default_address.exists():
            default_address = _q_default_address[0]
        else:
            default_address = None
            validated_data["is_default"] = True
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCSAddress, "手工创建")
        if validated_data["is_default"] and default_address:
            default_address.is_default = False
            default_address.save()
            logging(default_address, user, LogCSAddress, "由于创建新地址被取消默认")
            instance.is_default = True
            instance.save()
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if 'is_default' in validated_data:
            _q_default_address = self.Meta.model.objects.filter(customer=instance.customer, is_default=True)
            if _q_default_address.exists():
                default_address = _q_default_address[0]
                default_address.is_default = False
                default_address.save()
                logging(default_address, user, LogCSAddress, "更新默认被取消默认")
        if 'address' in validated_data:
            if validated_data["address"] != instance.address:
                _spilt_addr = PickOutAdress(validated_data["address"])
                _rt_addr = _spilt_addr.pickout_addr()

                if not isinstance(_rt_addr, dict):
                    raise ValidationError({"创建错误": "地址无法提取省市区"})
                validated_data["city"] = _rt_addr["city"]
            else:
                raise ValidationError({"创建错误": "无法获取地址！"})
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCSAddress, "修改内容：%s" % str(content))
        return instance
