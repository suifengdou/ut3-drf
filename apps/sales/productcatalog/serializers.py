import datetime
from django.db.models import Avg,Sum,Max,Min
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import ProductCatalog
from apps.utils.logging.loggings import logging


class ProductCatalogSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ProductCatalog
        fields = "__all__"

    def get_company(self, instance):
        try:
            ret = {
                "id": instance.company.id,
                "name": instance.company.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

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

    def get_order_status(self, instance):
        order_status = {
            0: "下架",
            1: "上架",
        }
        ret = {
            "id": instance.order_status,
            "name": order_status.get(instance.order_status, None)
        }
        return ret

    def to_representation(self, instance):
        ret = super(ProductCatalogSerializer, self).to_representation(instance)
        try:
            ret["company"] = self.get_company(instance)
            ret["goods"] = self.get_goods(instance)
            ret["department"] = self.get_department(instance)
            ret["order_status"] = self.get_order_status(instance)
        except:
            error = {"id": -1, "name": "显示错误"}
            ret["order_status"] = error
            ret["user"] = error
            ret["balance"] = error
        return ret

    def to_internal_value(self, data):
        return super(ProductCatalogSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["department"] = user.department
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


# class FreightSerializer(serializers.ModelSerializer):
#     create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
#     update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
#
#     class Meta:
#         model = Freight
#         fields = "__all__"
#
#     def get_company(self, instance):
#         try:
#             ret = {
#                 "id": instance.company.id,
#                 "name": instance.company.name
#             }
#         except:
#             ret = {
#                 "id": -1,
#                 "name": "空"
#             }
#         return ret
#
#     def get_goods(self, instance):
#         try:
#             ret = {
#                 "id": instance.goods.id,
#                 "name": instance.goods.name
#             }
#         except:
#             ret = {
#                 "id": -1,
#                 "name": "空"
#             }
#         return ret
#
#     def get_department(self, instance):
#         try:
#             ret = {
#                 "id": instance.department.id,
#                 "name": instance.department.name
#             }
#         except:
#             ret = {
#                 "id": -1,
#                 "name": "空"
#             }
#         return ret
#
#     def get_order_status(self, instance):
#         order_status = {
#             0: "下架",
#             1: "上架",
#         }
#         ret = {
#             "id": instance.order_status,
#             "name": order_status.get(instance.order_status, None)
#         }
#         return ret
#
#     def to_representation(self, instance):
#         ret = super(FreightSerializer, self).to_representation(instance)
#         try:
#             ret["company"] = self.get_company(instance)
#             ret["goods"] = self.get_goods(instance)
#             ret["department"] = self.get_department(instance)
#             ret["order_status"] = self.get_order_status(instance)
#         except:
#             error = {"id": -1, "name": "显示错误"}
#             ret["order_status"] = error
#             ret["user"] = error
#             ret["balance"] = error
#         return ret
#
#     def to_internal_value(self, data):
#         return super(FreightSerializer, self).to_internal_value(data)
#
#     def create(self, validated_data):
#         user = self.context["request"].user
#         validated_data["department"] = user.department
#         validated_data["creator"] = user.username
#         return self.Meta.model.objects.create(**validated_data)
#
#     def update(self, instance, validated_data):
#         user = self.context["request"].user
#         validated_data["updated_time"] = datetime.datetime.now()
#         # 改动内容
#         content = []
#         for key, value in validated_data.items():
#             if 'time' not in str(key):
#                 check_value = getattr(instance, key, None)
#                 if value != check_value:
#                     content.append('%s 替换 %s' % (value, check_value))
#
#         self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
#         logging(instance, user, LogFreight, "修改内容：%s" % str(content))
#         return instance



