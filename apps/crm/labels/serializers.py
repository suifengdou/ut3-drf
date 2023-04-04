import datetime, re
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import LabelCategory, Label, LogLabelCategory, LogLabel, LabelCustomerOrder, LabelCustomerOrderDetails, \
    LogLabelCustomerOrder, LabelCustomerOrderDetails, LogLabelCustomerOrderDetails
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
        validated_data["updated_time"] = datetime.datetime.now()
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

    def get_group(self, instance):
        GROUP_LIST = {
            "PPL": "基础",
            "FAM": "拓展",
            "PROD": "产品",
            "ORD": "交易",
            "SVC": "服务",
            "SAT": "体验",
            "REFD": "退换",
            "OTHS": "其他",

        }
        try:
            ret = {
                "id": instance.group,
                "name": GROUP_LIST.get(instance.group, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(LabelSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["group"] = self.get_group(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        serial_number = re.sub("[- .:]", "", str(datetime.datetime.now()))
        validated_data["code"] = serial_number
        instance = self.Meta.model.objects.create(**validated_data)
        instance.code = "%s-%s" % (instance.group, instance.id)
        instance.save()
        logging(instance, user, LogLabel, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        if "group" in validated_data:
            if validated_data["group"] != instance.group:
                validated_data["code"] = "%s-%s" % (instance.group, instance.id)
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

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "未处理",
            2: "未递交",
            3: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "存在未递交的明细",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_completed_quantity(self, instance):
        ret = instance.labelcustomerorderdetails_set.filter(order_status=2).count()
        return ret

    def to_representation(self, instance):
        ret = super(LabelCustomerOrderSerializer, self).to_representation(instance)
        ret["label"] = self.get_label(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["completed_quantity"] = self.get_completed_quantity(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        current_date = datetime.datetime.today().date()
        serial_number = re.sub("[- .:]", "", str(current_date))
        validated_data["name"] = f'{user.department.name}-{validated_data["label"].name}-{serial_number}-{user.username}'
        validated_data["code"] = f"{validated_data['label'].code}-{serial_number}"
        instance = self.Meta.model.objects.create(**validated_data)
        instance.name = "%s-%s" % (instance.name, instance.id)
        instance.code = "%s-%s" % (instance.code, instance.id)
        instance.save()
        logging(instance, user, LogLabelCustomerOrder, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        if 'label' in validated_data:
            completed_quantity = self.get_completed_quantity(instance)
            if validated_data["label"] != instance.label:
                if completed_quantity == 0:
                    current_date = datetime.datetime.today().date()
                    serial_number = re.sub("[- .:]", "", str(current_date))
                    validated_data["name"] = f'{user.department.name}-{validated_data["label"].name}-{serial_number}-{user.username}-{instance.id}'
                    validated_data["code"] = f'{validated_data["label"].code}-{serial_number}-{instance.id}'
                else:
                    raise serializers.ValidationError({"更改错误": "已存在完成明细的标签单禁止更改标签！"})
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
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

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "明细对应标签单状态错误",
            2: "明细未锁定",
            3: "标签已被删除恢复失败",
            4: "标签已存在不可重复打标",
            5: "标签打标失败",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "未处理",
            2: "未递交",
            3: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
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
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        _q_detail = self.Meta.model.objects.filter(order=validated_data["order"], customer=validated_data["customer"])
        if _q_detail.exists():
            raise serializers.ValidationError({"创建错误": "标签单明细中已存在此客户！"})
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogLabelCustomerOrderDetails, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
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

