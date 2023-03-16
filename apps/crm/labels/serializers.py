import datetime, re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import LabelCategory, Label, LogLabelCategory, LogLabel, LabelCustomerOrder, LabelCustomerOrderDetails, \
    LabelCustomer, LogLabelCustomerOrder, LogLabelCustomer, LabelCustomerOrderDetails, LogLabelCustomerOrderDetails
from apps.utils.logging.loggings import logging


class LabelCategorySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")


    class Meta:
        model = LabelCategory
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(LabelCategorySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogLabelCategory, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["update_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogLabelCategory, "修改内容：%s" % str(content))
        return instance


class LabelSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    code = serializers.CharField(required=False)

    class Meta:
        model = Label
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

    def get_center(self, instance):
        try:
            ret = {
                "id": instance.center.id,
                "name": instance.center.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(LabelSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["center"] = self.get_center(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
        validated_data["center"] = user.department.center
        validated_data["code"] = serial_number
        instance = self.Meta.model.objects.create(**validated_data)
        instance.code = "%s-%s-%s" % (instance.center.c_id, instance.category.code, instance.id)
        instance.save()
        logging(instance, user, LogLabel, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["update_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogLabel, "修改内容：%s" % str(content))
        return instance


class LabelCustomerOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    name = serializers.CharField(required=False)
    code = serializers.CharField(required=False)

    class Meta:
        model = LabelCustomerOrder
        fields = "__all__"

    def get_label(self, instance):
        try:
            ret = {
                "id": instance.label.id,
                "name": instance.label.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(LabelCustomerOrderSerializer, self).to_representation(instance)
        ret["label"] = self.get_label(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        current_date = datetime.datetime.today().date()
        serial_number = re.sub("[- .:]", "", str(current_date))
        validated_data["name"] = '%s-%s-%s-%s' % (user.department.center.name, validated_data["label"].name, serial_number, user.username)
        validated_data["code"] = "%s-%s" % (validated_data["label"].code, serial_number)
        instance = self.Meta.model.objects.create(**validated_data)
        instance.name = "%s-%s" % (instance.name, instance.id)
        instance.code = "%s-%s" % (instance.code, instance.id)
        instance.save()
        logging(instance, user, LogLabelCustomerOrder, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["update_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        current_date = datetime.datetime.today().date()
        serial_number = re.sub("[- .:]", "", str(current_date))
        validated_data["name"] = '%s-%s-%s-%s-%s' % (user.department.center.name, validated_data["label"].name,
                                                     serial_number, user.username, instance.id)
        validated_data["code"] = "%s-%s-%s" % (validated_data["label"].code, serial_number, instance.id)
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogLabelCustomerOrder, "修改内容：%s" % str(content))
        return instance


class LabelCustomerOrderDetailsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = LabelCustomerOrderDetails
        fields = "__all__"

    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

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

    def to_representation(self, instance):
        ret = super(LabelCustomerOrderDetailsSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["customer"] = self.get_customer(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogLabelCustomerOrderDetails, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["update_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogLabelCustomerOrderDetails, "修改内容：%s" % str(content))
        return instance


class LabelCustomerSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = LabelCustomer
        fields = "__all__"

    def get_label(self, instance):
        try:
            ret = {
                "id": instance.label.id,
                "name": instance.label.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

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

    def get_center(self, instance):
        try:
            ret = {
                "id": instance.center.id,
                "name": instance.center.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(LabelCustomerSerializer, self).to_representation(instance)
        ret["label"] = self.get_label(instance)
        ret["customer"] = self.get_customer(instance)
        ret["center"] = self.get_center(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogLabelCustomer, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["update_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:

                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogLabelCategory, "修改内容：%s" % str(content))
        return instance


