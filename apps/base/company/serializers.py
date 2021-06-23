from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    CATEGORY = (
        (0, '小狗体系'),
        (1, '物流快递'),
        (2, '仓库存储'),
        (3, '生产制造'),
        (4, '经销代理'),
        (5, '其他类型'),
    )
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '正常'),
    )

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    category = serializers.ChoiceField(
        choices=CATEGORY, help_text="类型"
    )

    class Meta:
        model = Company
        fields = "__all__"


    def to_representation(self, instance):
        ret = super(CompanySerializer, self).to_representation(instance)
        try:
            ret["category"] = self.__class__.CATEGORY[ret["category"]][1]
            ret["order_status"] = self.__class__.ORDER_STATUS[ret["order_status"]][1]
        except:
            ret["category"] = '分类错误'
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance