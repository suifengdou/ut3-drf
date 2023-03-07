import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, LogCustomer
from apps.crm.labels.models import Label, LabelCustomer, LogLabelCustomer
from apps.utils.logging.loggings import logging


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomer, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('%s 替换 %s' % (value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomer, "修改内容：%s" % str(content))
        return instance


class CustomerLabelSerializer(serializers.ModelSerializer):
    label_add = serializers.JSONField(required=False)

    class Meta:
        model = Customer
        fields = "__all__"

    def get_labels(self, instance):
        labels = instance.labelcustomer_set.all()
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(CustomerLabelSerializer, self).to_representation(instance)
        ret["labels"] = self.get_labels(instance)
        return ret

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if validated_data["label_add"]:
            _q_label = Label.objects.filter(id=validated_data["label_add"])
            if _q_label.exists():
                try:
                    order_dict = {
                        "customer": instance,
                        "label": _q_label[0],
                        "center": user.department.center,
                        "memo": "%s 手工创建" % user.username,
                    }
                except Exception as e:
                    raise serializers.ValidationError("登陆账号没有设置公司或者部门，不可以创建！")
                label_customer = LabelCustomer.objects.create(**order_dict)
                logging(label_customer, user, LogLabelCustomer, "手工创建")
                logging(instance, user, LogCustomer, "手工创建标签：%s" % order_dict["label"].name)
        return instance



