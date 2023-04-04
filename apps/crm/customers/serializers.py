import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, LogCustomer
from apps.crm.labels.models import Label
from apps.utils.logging.loggings import logging
from apps.crm.customerlabel.views import QueryLabel, CreateLabel, DeleteLabel, RecoverLabel


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
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomer, "修改内容：%s" % str(content))
        return instance


class CustomerLabelSerializer(serializers.ModelSerializer):
    add_label = serializers.JSONField(required=False)
    del_label = serializers.JSONField(required=False)

    class Meta:
        model = Customer
        fields = "__all__"

    def get_label_person(self, instance):
        labels = instance.customerlabelperson_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_family(self, instance):
        labels = instance.customerlabelfamily_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_product(self, instance):
        labels = instance.customerlabelproduct_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_order(self, instance):
        labels = instance.customerlabelorder_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_service(self, instance):
        labels = instance.customerlabelservice_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_satisfaction(self, instance):
        labels = instance.customerlabelsatisfaction_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_refund(self, instance):
        labels = instance.customerlabelrefund_set.filter(is_delete=False)
        ret = []
        if labels:
            for label in labels:
                data = {
                    "id": label.label.id,
                    "name": label.label.name,
                }
                ret.append(data)
        return ret

    def get_label_others(self, instance):
        labels = instance.customerlabelothers_set.filter(is_delete=False)
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
        ret["label_person"] = self.get_label_person(instance)
        ret["label_family"] = self.get_label_family(instance)
        ret["label_product"] = self.get_label_product(instance)
        ret["label_order"] = self.get_label_order(instance)
        ret["label_service"] = self.get_label_service(instance)
        ret["label_satisfaction"] = self.get_label_satisfaction(instance)
        ret["label_refund"] = self.get_label_refund(instance)
        ret["label_others"] = self.get_label_others(instance)
        return ret

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if "add_label" in validated_data:
            add_labels = str(validated_data["add_label"]).split()
            for label in add_labels:
                _q_label = Label.objects.filter(name=str(label), is_cancel=False)
                if len(_q_label) == 1:
                    label_obj = _q_label[0]
                    _q_check_add_label_order = QueryLabel(label_obj, instance)
                    if _q_check_add_label_order:
                        if _q_check_add_label_order.is_delete:
                            _recover_result = RecoverLabel(_q_check_add_label_order, label_obj, user)
                            if _recover_result:
                                continue
                        else:
                            raise serializers.ValidationError({"创建错误": f"已存在标签：{label_obj.name}，不可重复创建！"})
                    else:
                        _created_result = CreateLabel(label_obj, instance, user)
                        if not _created_result:
                            raise serializers.ValidationError({"创建错误": "创建标签单出现错误"})
                else:
                    raise serializers.ValidationError({"创建错误": f"标签名称错误：{str(label)}，输入标准标签名称！"})

        if "del_label" in validated_data:
            del_labels = str(validated_data["del_label"]).split()
            for label in del_labels:
                _q_label = Label.objects.filter(name=str(label), is_cancel=False)
                if len(_q_label) == 1:
                    label_obj = _q_label[0]
                    _q_check_del_label_order = QueryLabel(label_obj, instance)
                    if _q_check_del_label_order:
                        _deleted_result = DeleteLabel(label_obj, instance, user)
                        if not _deleted_result:
                            raise serializers.ValidationError({"删除错误": f"标签名称：{label_obj.name}，删除失败！"})
                    else:
                        raise serializers.ValidationError({"删除错误": f"标签名称：{label_obj.name}.在此客户中未找到！"})
                else:
                    raise serializers.ValidationError({"删除错误": f"标签名称错误：{str(label)}，输入标准标签名称！"})

        return instance



