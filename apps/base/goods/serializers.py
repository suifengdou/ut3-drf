import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Goods, GoodsCategory, Bom, LogBom, LogGoods, LogGoodsCategory
from apps.utils.logging.loggings import getlogs, logging


class GoodsSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Goods
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

    def get_goods_attribute(self, instance):
        goods_attribute = {
            1: "整机",
            2: "配件",
            3: "礼品",
        }
        try:
            ret = {
                "id": instance.goods_attribute,
                "name": goods_attribute.get(instance.goods_attribute, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(GoodsSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["goods_attribute"] = self.get_goods_attribute(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogGoods, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogGoods, "修改内容：%s" % str(content))
        return instance


class GoodsCategorySerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = GoodsCategory
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(GoodsCategorySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogGoodsCategory, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogGoodsCategory, "修改内容：%s" % str(content))
        return instance


class BomSerializer(serializers.ModelSerializer):
    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Bom
        fields = "__all__"

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_part(self, instance):
        try:
            ret = {
                "id": instance.part.id,
                "name": instance.part.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(BomSerializer, self).to_representation(instance)
        ret["goods"] = self.get_goods(instance)
        ret["part"] = self.get_part(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        if validated_data["goods"].goods_attribute != 1:
            raise ValidationError({"创建错误": "货品项必须为整机"})
        if validated_data["part"].goods_attribute != 2:
            raise ValidationError({"创建错误": "配件项必须为配件"})
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogBom, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        if validated_data["goods"].goods_attribute != 1:
            raise ValidationError({"更新错误": "货品项必须为整机"})
        if validated_data["part"].goods_attribute != 2:
            raise ValidationError({"更新错误": "配件项必须为配件"})
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogBom, "修改内容：%s" % str(content))
        return instance








