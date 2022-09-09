import datetime
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import OriCallLog, CallLog


class OriCallLogSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriCallLog
        fields = "__all__"

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "待提取",
            2: "未处理",
            3: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "重复建单",
            2: "无补寄原因",
            3: "非赠品必填项错误",
            4: "店铺错误",
            5: "手机错误",
            6: "地址无法提取省市区",
            7: "地址是集运仓",
            8: "输出单保存出错",
            9: "货品错误",
            10: "明细中货品重复、部件和描述",
            11: "输出单保存出错",
            12: "未处理单据不可递交",
            13: "已经存在检查单",
            14: "保存检查单错误",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理",
            2: "驳回",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(OriCallLogSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        return ret

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("price", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class CallLogSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = CallLog
        fields = "__all__"

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未处理",
            2: "待执行",
            3: "待确认",
            4: "已完成",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "主观类型必填处理意见",
            2: "未标记工单不可审核",
            3: "无驳回原因不可驳回",
            4: "无执行结果不可审核",
            5: "输出单保存出错",
            6: "同名订单",
            7: "手机错误",
            8: "集运仓地址",
            9: "无店铺",
            10: "售后配件需要补全sn、部件和描述",
            11: "无部门",
            12: "缺货",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理",
            2: "驳回",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_question_tag(self, instance):
        question_list = {
            0: "未标记",
            1: "客服问题",
            2: "未能转人工",
            3: "非服务时间",
            4: "常规复咨询",
            5: "用户问题",
            6: "其他",
        }
        try:
            ret = {
                "id": instance.question_tag,
                "name": question_list.get(instance.question_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(CallLogSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["question_tag"] = self.get_question_tag(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance





