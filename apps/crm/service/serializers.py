import datetime
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import OriMaintenance, Maintenance, MaintenanceSummary, OriMaintenanceGoods, MaintenanceGoods, LogOriMaintenance, LogOriMaintenanceGoods, LogMaintenance, LogMaintenanceGoods, LogMaintenanceSummary
from apps.utils.logging.loggings import logging


class OriMaintenanceSerializer(serializers.ModelSerializer):
    check_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=False, label="预约时间", help_text="预约时间")
    purchase_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=False, label="购买时间", help_text="购买时间")
    handle_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=False, label="审核时间", help_text="审核时间")
    ori_created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=False, label="原始创建时间", help_text="原始创建时间")
    finish_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=False, label="完成时间", help_text="完成时间")
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriMaintenance
        fields = "__all__"

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未处理",
            2: "已递交",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "无异常",
            1: "审核异常",
            2: "逆向异常",
            3: "取件异常",
            4: "入库异常",
            5: "维修异常",
            6: "超期异常",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign(self, instance):
        SIGN_LIST = {
            0: "无",
            1: "处理完毕",
            2: "配件缺货",
            3: "延后处理",
            4: "快递异常",
            5: "特殊问题",
            6: "处理收费",
            7: "其他情况"
        }
        try:
            ret = {
                "id": instance.sign,
                "name": SIGN_LIST.get(instance.sign, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "单据货品为空导致出错",
            2: "货品名称无法提取到整机型号",
            3: "备注格式错误",
            4: "不可重复递交",
            5: "UT系统无此店铺",
            6: "UT系统无此仓库",
            7: "未解密的单据不可递交",
            8: "以旧换新类型",
            9: "寄回区域无法提取省市",
            10: "创建出错",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
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
        ret = super(OriMaintenanceSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["sign"] = self.get_sign(instance)
        ret["goods"] = self.get_goods(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        _q_detail = self.Meta.model.objects.filter(order_id=validated_data["order_id"])
        if _q_detail.exists():
            raise serializers.ValidationError({"创建错误": "标签单明细中已存在此单据！"})
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogOriMaintenance, "创建")
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
        logging(instance, user, LogOriMaintenance, "修改内容：%s" % str(content))
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

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name,
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

    def get_ori_order(self, instance):
        try:
            ret = {
                "id": instance.ori_order.id,
                "name": instance.ori_order.order_id,
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

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret


    def get_process_tag(self, instance):
        status_list = {
            0: "未锁定",
            1: "未处理",
            2: "已处理",
            9: "特殊订单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": status_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未处理",
            2: "已递交",
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
        ret["goods"] = self.get_goods(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["ori_order"] = self.get_ori_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["customer"] = self.get_customer(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        _q_detail = self.Meta.model.objects.filter(order_id=validated_data["order_id"])
        if _q_detail.exists():
            raise serializers.ValidationError({"创建错误": "标签单明细中已存在此单据！"})
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogMaintenance, "创建")
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
        logging(instance, user, LogMaintenance, "修改内容：%s" % str(content))
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


class OriMaintenanceGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriMaintenanceGoods
        fields = "__all__"

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未处理",
            2: "已递交",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "无异常",
            1: "审核异常",
            2: "逆向异常",
            3: "取件异常",
            4: "入库异常",
            5: "维修异常",
            6: "超期异常",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign(self, instance):
        SIGN_LIST = {
            0: "无",
            1: "处理完毕",
            2: "配件缺货",
            3: "延后处理",
            4: "快递异常",
            5: "特殊问题",
            6: "处理收费",
            7: "其他情况"
        }
        try:
            ret = {
                "id": instance.sign,
                "name": SIGN_LIST.get(instance.sign, None)
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
            7: "递交到保修单错乱",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
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
        ret = super(OriMaintenanceGoodsSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["sign"] = self.get_sign(instance)
        ret["goods"] = self.get_goods(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        _q_detail = self.Meta.model.objects.filter(order_id=validated_data["order_id"])
        if _q_detail.exists():
            raise serializers.ValidationError({"创建错误": "标签单明细中已存在此单据！"})
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogOriMaintenanceGoods, "创建")
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
        logging(instance, user, LogOriMaintenanceGoods, "修改内容：%s" % str(content))
        return instance


class MaintenanceGoodsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = MaintenanceGoods
        fields = "__all__"

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "未处理",
            2: "已递交",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "无异常",
            1: "审核异常",
            2: "逆向异常",
            3: "取件异常",
            4: "入库异常",
            5: "维修异常",
            6: "超期异常",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_sign(self, instance):
        SIGN_LIST = {
            0: "无",
            1: "处理完毕",
            2: "配件缺货",
            3: "延后处理",
            4: "快递异常",
            5: "特殊问题",
            6: "处理收费",
            7: "其他情况"
        }
        try:
            ret = {
                "id": instance.sign,
                "name": SIGN_LIST.get(instance.sign, None)
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
            7: "递交到保修单错乱",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
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
        ret = super(MaintenanceGoodsSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["sign"] = self.get_sign(instance)
        ret["goods"] = self.get_goods(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        _q_detail = self.Meta.model.objects.filter(order_id=validated_data["order_id"])
        if _q_detail.exists():
            raise serializers.ValidationError({"创建错误": "标签单明细中已存在此单据！"})
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogOriMaintenance, "创建")
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
        logging(instance, user, LogOriMaintenance, "修改内容：%s" % str(content))
        return instance





