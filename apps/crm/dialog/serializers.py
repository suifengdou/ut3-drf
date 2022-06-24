import datetime
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Servicer, DialogTB, DialogTBDetail, DialogTBWords, DialogJD, DialogJDDetail, DialogJDWords, \
    DialogOW, DialogOWDetail, DialogOWWords


class ServicerSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Servicer
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

    def get_username(self, instance):
        try:
            ret = {
                "id": instance.username.id,
                "name": instance.username.username,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_category(self, instance):
        category_list = {
            0: "机器人",
            1: "人工",
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(ServicerSerializer, self).to_representation(instance)
        ret["shop"] = self.get_shop(instance)
        ret["username"] = self.get_username(instance)
        ret["category"] = self.get_category(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogTBSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogTB
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(DialogTBSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogTBDetailSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    class Meta:
        model = DialogTBDetail
        fields = "__all__"

    def get_dialog(self, instance):
        try:
            ret = {
                "id": instance.dialog.id,
                "name": instance.dialog.customer,
                "shop": instance.dialog.shop
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_d_status(self, instance):
        status_list = {
            0: "顾客",
            1: "客服",
            2: "机器人"
        }
        try:
            ret = {
                "id": instance.d_status,
                "name": status_list.get(instance.d_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_category(self, instance):
        category_list = {
            0: "常规",
            1: "订单",
            2: "差价"
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "重复递交，已存在输出单据",
            2: "对话的格式错误",
            3: "收货人手机地址顺序错误或者手机错误",
            4: "地址无法提取省市区",
            5: "地址是集运仓",
            6: "输出单保存出错",
            7: "UT中不存在此货品",
            8: "货品错误",
            9: "明细中货品重复",
            10: "货品输出单保存出错",
            11: "差价必要信息缺失",
            12: "差价类型只能填1或3",
            13: "差价验算公式错误",
            14: "差价验算结果和差价不等",
            15: "保存差价申请单出错",
            16: "被丢弃"
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "被取消",
            1: "未过滤",
            2: "未分词",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret
        pass

    def to_representation(self, instance):
        ret = super(DialogTBDetailSerializer, self).to_representation(instance)
        ret["dialog"] = self.get_dialog(instance)
        ret["d_status"] = self.get_d_status(instance)
        ret["category"] = self.get_category(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogTBWordsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogTBWords
        fields = "__all__"

    def get_dialog_detail(self, instance):
        try:
            ret = {
                "id": instance.dialog_detail.id,
                "name": instance.dialog_detail.sayer,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(DialogTBWordsSerializer, self).to_representation(instance)
        ret["dialog_detail"] = self.get_dialog_detail(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogJDSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogJD
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(DialogJDSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogJDDetailSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    class Meta:
        model = DialogJDDetail
        fields = "__all__"

    def get_dialog(self, instance):
        try:
            ret = {
                "id": instance.dialog.id,
                "name": instance.dialog.customer,
                "shop": instance.dialog.shop
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret


    def get_d_status(self, instance):
        status_list = {
            0: "顾客",
            1: "客服",
            2: "机器人"
        }
        try:
            ret = {
                "id": instance.d_status,
                "name": status_list.get(instance.d_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_category(self, instance):
        category_list = {
            0: "常规",
            1: "订单",
            2: "差价"
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
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
            10: "明细中货品重复",
            11: "输出单保存出错",
            12: "被丢弃"
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "被取消",
            1: "未过滤",
            2: "未分词",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret
        pass

    def to_representation(self, instance):
        ret = super(DialogJDDetailSerializer, self).to_representation(instance)
        ret["dialog"] = self.get_dialog(instance)
        ret["d_status"] = self.get_d_status(instance)
        ret["category"] = self.get_category(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogJDWordsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogJDWords
        fields = "__all__"

    def get_dialog_detail(self, instance):
        try:
            ret = {
                "id": instance.dialog_detail.id,
                "name": instance.dialog_detail.sayer,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(DialogJDWordsSerializer, self).to_representation(instance)
        ret["dialog_detail"] = self.get_dialog_detail(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogOWSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogOW
        fields = "__all__"

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
            12: "被丢弃"
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status_list = {
            0: "被取消",
            1: "未过滤",
            2: "未分词",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret
        pass


    def to_representation(self, instance):
        ret = super(DialogOWSerializer, self).to_representation(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogOWDetailSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    class Meta:
        model = DialogOWDetail
        fields = "__all__"

    def get_dialog(self, instance):
        try:
            ret = {
                "id": instance.dialog.id,
                "name": instance.dialog.customer,
                "shop": instance.dialog.shop
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_d_status(self, instance):
        status_list = {
            0: "客服",
            1: "顾客"
        }
        try:
            ret = {
                "id": instance.d_status,
                "name": status_list.get(instance.d_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_category(self, instance):
        category_list = {
            0: "常规",
            1: "订单",
            2: "差价"
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(DialogOWDetailSerializer, self).to_representation(instance)
        ret["dialog"] = self.get_dialog(instance)
        ret["d_status"] = self.get_d_status(instance)
        ret["category"] = self.get_category(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class DialogOWWordsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = DialogOWWords
        fields = "__all__"

    def get_dialog_detail(self, instance):
        try:
            ret = {
                "id": instance.dialog_detail.id,
                "name": instance.dialog_detail.sayer,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(DialogOWWordsSerializer, self).to_representation(instance)
        ret["dialog_detail"] = self.get_dialog_detail(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance



