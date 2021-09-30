import datetime
from functools import reduce
from django.db.models import Sum, Avg, Count
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Compensation, BatchCompensation, BCDetail


class CompensationSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Compensation
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

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_category(self, instance):
        category = {
            1: "差价补偿",
            2: "错误重置",
            3: "退货退款",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未处理",
            2: "已完成",
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
            1: "重复创建",
            2: "重复递交",
            3: "保存批次单明细失败"
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
            2: "特殊订单",
            3: "重置订单",
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
        ret = super(CompensationSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def validate(self, attrs):
        if all([attrs.get("checking", None), attrs.get("actual_receipts", None), attrs.get("receivable", None), attrs.get("compensation", None)]):
            if float(attrs["checking"]) != float(attrs["actual_receipts"]) - float(attrs["receivable"]):
                raise serializers.ValidationError("验算公式错误！")
            if float(attrs["checking"]) != float(attrs["compensation"]):
                raise serializers.ValidationError("验算结果与补偿金额不同！")
        return attrs

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class BatchCompensationSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = BatchCompensation
        fields = "__all__"

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未处理",
            2: "未结算",
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

    def get_order_category(self, instance):
        category_list = {
            1: "差价补偿",
            2: "错误重置",
            3: "退货退款",
        }
        try:
            ret = {
                "id": instance.order_category,
                "name": category_list.get(instance.order_category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_shop(self, instance):
        try:
            ret = {
                "id": instance.shop.id,
                "name": instance.shop.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "无OA单号",
            2: "有未完成的明细"
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
            2: "特殊订单",
            3: "重置订单",
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
        ret = super(BatchCompensationSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["order_category"] = self.get_order_category(instance)
        ret["shop"] = self.get_shop(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)

        compensation_details = instance.bcdetail_set.all()
        ret["amount"] = compensation_details.aggregate(amount=Sum("compensation"))["amount"]
        ret["paid_amount"] = compensation_details.aggregate(paid_amount=Sum("paid_amount"))["paid_amount"]
        if ret["amount"] == None:
            ret["amount"] = 0
        if ret["paid_amount"] == None:
            ret["paid_amount"] = 0
        ret["count"] = compensation_details.count()
        ret["compensation_details"] = []
        for compensation_detail in compensation_details:
            data = {
                "id": compensation_detail.id,
                "goods_name": compensation_detail.goods_name.name,
                "compensation": compensation_detail.compensation,
                "name": compensation_detail.name,
                "alipay_id": compensation_detail.alipay_id,
                "paid_amount": compensation_detail.paid_amount,
                "memorandum": compensation_detail.memorandum
            }
            ret["compensation_details"].append(data)

        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class BCDetailSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = BCDetail
        fields = "__all__"

    def get_batch_order(self, instance):
        category_list = {
            1: "差价补偿",
            2: "错误重置",
            3: "退货退款",
        }
        try:
            ret = {
                "id": instance.batch_order.id,
                "order_id": instance.batch_order.order_id,
                "shop": instance.batch_order.shop.name,
                "order_category": category_list.get(instance.batch_order.order_category, None),
                "oa_order_id": instance.batch_order.oa_order_id,
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

    def get_order_status(self, instance):
        status = {
            0: "已取消",
            1: "未处理",
            2: "未结算",
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
            1: "已付金额不是零，不可重置",
            2: "重置保存补偿单出错",
            3: "补运费和已付不相等",
            4: "补寄配件记录格式错误",
            5: "补寄原因错误",
            6: "单据创建失败"
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
            0: "无异常",
            1: "无效支付宝",
            2: "支付宝和收款人不匹配",
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
        ret = super(BCDetailSerializer, self).to_representation(instance)
        ret["batch_order"] = self.get_batch_order(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        return ret

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance




