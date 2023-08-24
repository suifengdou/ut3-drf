import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CNOrder, HistoryCNOrder, LogCNOrder, LogHistoryCNOrder
from apps.utils.logging.loggings import logging


class CNOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    pay_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", label="付款时间", help_text="付款时间")
    deliver_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", label="发货时间", help_text="发货时间")

    class Meta:
        model = CNOrder
        fields = "__all__"

    def get_process_tag(self, instance):
        process_list = {
            0: '未处理',
            1: '已处理',
            2: '驳回',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
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
            1: "已导入过的订单",
            2: "UT中无此店铺",
            3: "UT中店铺关联平台",
            4: "保存出错",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": mistake_list.get(instance.process_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name
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
            2: "未标记",
            3: "未财审",
            4: "已完成",
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
        ret = super(CNOrderSerializer, self).to_representation(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["shop"] = self.get_shop(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

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
        if all([validated_data["receiver"], validated_data["mobile"], validated_data["address"]]):
            validated_data["process_tag"] = 1

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCNOrder, "修改内容：%s" % str(content))
        return instance


class HistoryCNOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = HistoryCNOrder
        fields = "__all__"

    def get_process_tag(self, instance):
        process_list = {
            0: '未处理',
            1: '已处理',
            2: '驳回',
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
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
            1: "已导入过的订单",
            2: "UT中无此店铺",
            3: "UT中店铺关联平台",
            4: "保存出错",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": mistake_list.get(instance.process_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name
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
            2: "未标记",
            3: "未财审",
            4: "已完成",
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
        ret = super(HistoryCNOrderSerializer, self).to_representation(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["shop"] = self.get_shop(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

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
        logging(instance, user, LogHistoryCNOrder, "修改内容：%s" % str(content))
        return instance




