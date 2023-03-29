import datetime, re
from django.db.models import Sum, Count
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import JobCategory, JobOrder, JOFiles, JobOrderDetails, LogJobCategory, LogJobOrder, \
    LogJobOrderDetails, JODFiles
from apps.utils.logging.loggings import logging


class JobCategorySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = JobCategory
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(JobCategorySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogJobCategory, "创建")
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
        logging(instance, user, LogJobCategory, "修改内容：%s" % str(content))
        return instance


class JobOrderSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    code = serializers.CharField(required=False)

    class Meta:
        model = JobOrder
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

    def get_department(self, instance):
        try:
            ret = {
                "id": instance.department.id,
                "name": instance.department.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

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

    def get_process_tag(self, instance):
        process_tag = {
            0: "未处理",
            1: "已处理",
            5: "特殊订单",
            9: "驳回",

        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_tag = {
            0: "正常",
            1: "任务明细未完整确认",
            2: "先锁定再审核",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_tag.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待处理",
            2: "待领取",
            3: "待执行",
            4: "待审核",
            5: "已完成",

        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_complete_number(self, instance):
        ret = instance.joborderdetails_set.filter(is_complete=True).count()
        return ret

    def get_over_number(self, instance):
        ret = instance.joborderdetails_set.filter(is_over=True).count()
        return ret

    def to_representation(self, instance):
        ret = super(JobOrderSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["center"] = self.get_center(instance)
        ret["department"] = self.get_department(instance)
        ret["label"] = self.get_label(instance)
        ret["complete_number"] = self.get_complete_number(instance)
        ret["over_number"] = self.get_over_number(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        if instance.order_status == 2 and instance.quantity == ret["over_number"]:
            user = self.context["request"].user
            instance.order_status = 3
            instance.save()
            logging(instance, user, LogJobOrder, "系统自动完结已完结的任务工单")
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
        logging(instance, user, LogJobOrder, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if any(('TEMP' in validated_data["code"], validated_data["label"] != instance.label, validated_data["category"] != instance.category)):
            if not all((validated_data["label"], validated_data['category'])):
                raise serializers.ValidationError({"更新错误": "标签和类型为必填字段！"})
            serial_number = re.sub("[- .:]", "", str(datetime.datetime.today().date()))
            validated_data["name"] = '%s-%s-%s-%s-%s' % (validated_data["department"].name,
                                                         validated_data["category"].name, validated_data["label"].name,
                                                         serial_number, user.username)

            validated_data["code"] = '%s-%s-%s' % (validated_data["category"].code, validated_data["label"].code,
                                                   str(instance.id))
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
        logging(instance, user, LogJobOrder, "修改内容：%s" % str(content))
        return instance


class JobOrderDetailsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = JobOrderDetails
        fields = "__all__"

    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.name,
                "code": instance.order.code,
                "label": instance.order.label.name,
                "category": instance.order.category.name,
                "info": instance.order.info,
                "keywords": instance.order.keywords
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

    def get_process_tag(self, instance):
        process_tag = {
            0: "未处理",
            1: "已处理",
            5: "特殊订单",
            9: "驳回",

        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_tag = {
            0: "正常",
            1: "单据已锁定无法锁定",
            2: "先锁定再审核",
            3: "先设置完成按钮或结束按钮",
            4: "无操作内容",
            5: "标签创建错误",
            6: "标签删除错误",
            7: "工单默认标签创建错误",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_tag.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待处理",
            2: "待领取",
            3: "待执行",
            4: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "错误"}
        return ret

    def to_representation(self, instance):
        ret = super(JobOrderDetailsSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["customer"] = self.get_customer(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        instance.save()
        logging(instance, user, LogJobOrderDetails, "创建")
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
        logging(instance, user, LogJobOrderDetails, "修改内容：%s" % str(content))
        return instance


class JOFilesSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = JOFiles
        fields = "__all__"

    def get_creator(self, instance):
        try:
            ret = {
                "id": instance.creator.id,
                "name": instance.creator.username
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
            ret = super(JOFilesSerializer, self).to_representation(instance)
            ret['creator'] = self.get_creator(instance)
            return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class JODFilesSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = JODFiles
        fields = "__all__"

    def get_creator(self, instance):
        try:
            ret = {
                "id": instance.creator.id,
                "name": instance.creator.username
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
            ret = super(JODFilesSerializer, self).to_representation(instance)
            ret['creator'] = self.get_creator(instance)
            return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance

