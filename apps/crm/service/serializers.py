import datetime
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import OriMaintenance, Maintenance, FindAndFound, MaintenanceSummary


class OriMaintenanceSerializer(serializers.ModelSerializer):
    purchase_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="购买时间", help_text="购买时间")
    handle_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="审核时间", help_text="审核时间")
    ori_create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="原始创建时间", help_text="原始创建时间")
    finish_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="完成时间", help_text="完成时间")
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriMaintenance
        fields = "__all__"

    def get_towork_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未处理",
            2: "已导入",
        }
        try:
            ret = {
                "id": instance.towork_status,
                "name": status_list.get(instance.towork_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "未更新到",
            2: "取件超时",
            3: "到库超时",
            4: "维修超时",
            5: "特殊订单"
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "尝试修复数据",
            2: "二级市错误",
            3: "寄件地区出错",
            4: "UT无此店铺",
            5: "UT此型号整机未创建",
            6: "UT系统无此店铺",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(OriMaintenanceSerializer, self).to_representation(instance)
        ret["towork_status"] = self.get_towork_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class MaintenanceSerializer(serializers.ModelSerializer):
    handle_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="审核时间", help_text="审核时间")
    ori_create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="原始创建时间",
                                                help_text="原始创建时间")
    finish_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="完成时间", help_text="完成时间")
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_timdate_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Maintenance
        fields = "__all__"

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_province(self, instance):
        try:
            ret = {
                "id": instance.province.id,
                "name": instance.province.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.district.id,
                "name": instance.district.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_maintenance(self, instance):
        try:
            ret = {
                "id": instance.maintenance.id,
                "name": instance.maintenance.order_id,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_repeat_tag(self, instance):
        repeat_list = {
            0: "正常",
            1: "未处理",
            2: "产品",
            3: "维修",
            4: "其他",
        }
        try:
            ret = {
                "id": instance.repeat_tag,
                "name": repeat_list.get(instance.repeat_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未计算",
            2: "未处理",
            3: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(MaintenanceSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["maintenance"] = self.get_maintenance(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["customer"] = self.get_customer(instance)
        ret["repeat_tag"] = self.get_repeat_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class FindAndFoundSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = FindAndFound
        fields = "__all__"

    def get_find(self, instance):
        try:
            ret = {
                "finish_date": instance.find.finish_date,
                "id": instance.find.id,
                "shop": instance.find.shop.name,
                "goods_name": instance.find.goods_name.name,
                "name": instance.find.order_id,
                "warehouse": instance.find.warehouse,
                "machine_sn": instance.find.machine_sn,
                "appraisal": instance.find.appraisal,
                "description": instance.find.description,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_found(self, instance):
        try:
            ret = {
                "finish_date": instance.find.finish_date,
                "id": instance.found.id,
                "name": instance.found.order_id,
                "appraisal": instance.found.appraisal,
                "description": instance.found.description,
                "goods_name": instance.found.goods_name.name,
                "memo": instance.found.memo
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_repeat_tag(self, instance):
        repeat_list = {
            0: "正常",
            1: "未处理",
            2: "产品",
            3: "维修",
            4: "其他",
        }
        try:
            ret = {
                "id": instance.found.repeat_tag,
                "name": repeat_list.get(instance.found.repeat_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(FindAndFoundSerializer, self).to_representation(instance)
        ret["find"] = self.get_find(instance)
        ret["found"] = self.get_found(instance)
        ret["repeat_tag"] = self.get_repeat_tag(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class MaintenanceSummarySerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = MaintenanceSummary
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(MaintenanceSummarySerializer, self).to_representation(instance)
        return ret




