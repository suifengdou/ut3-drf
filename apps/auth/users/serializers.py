# -*- coding: utf-8 -*-
# @Time    : 2020/12/24 15:23
# @Author  : Hann
# @Site    : 
# @File    : serializers.py
# @Software: PyCharm

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
from rest_framework import status
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_login = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = User
        fields = "__all__"

    def get_groups(self, instance):
        groups = instance.groups.all()
        ret = []
        for group in groups:
            data = {
                "id": group.id,
                "name": group.name
            }
            ret.append(data)
        return ret

    def get_company(self, instance):
        data = {
            "id": instance.company.id,
            "name": instance.company.name
        }
        return data

    def get_department(self, instance):
        data = {
            "id": instance.department.id,
            "name": instance.department.name
        }
        return data

    def get_platform(self, instance):
        data = {
            "id": instance.platform.id,
            "name": instance.platform.name
        }
        return data

    def to_representation(self, instance):
            ret = super(UserSerializer, self).to_representation(instance)
            ret["password"] = '*****'
            try:
                ret["groups"] = self.get_groups(instance)
                ret["company"] = self.get_company(instance)
                ret["department"] = self.get_department(instance)
                ret["platform"] = self.get_platform(instance)
            except:
                fields = ["company", "department", "platform"]
                for key in fields:
                    ret[key] = {
                        "id": -1,
                        "name": "未设置"
                    }
            return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        groups_list = validated_data.pop("groups", [])
        user_permissions = validated_data.pop("user_permissions", [])
        validated_data['password'] = make_password(validated_data['password'])
        user = User.objects.create(**validated_data)
        user.groups.set(groups_list)
        user.user_permissions.set(user_permissions)
        return user

    def update(self, instance, validated_data):
        groups_list = validated_data.pop("groups", [])
        user_permissions = validated_data.pop("user_permissions", [])
        password = validated_data.pop("password", "")
        create_time = validated_data.pop("create_time", "")
        update_tim = validated_data.pop("update_tim", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        instance.groups.set(groups_list)
        instance.user_permissions.set(user_permissions)
        return instance


class UserPasswordSerializer(serializers.Serializer):

    password = serializers.CharField(required=True, max_length=128, label="密码", help_text="密码",
                                     error_messages={
                                         "blank": "不可以为空",
                                         "required": "必填项"}
                                     )
    def validate_password(self, value):
        validations = []
        password = value
        if len(password) < 5 or len(password) > 15:
            validations.append('密码必须大于5个字符，小于15个字符')
        if password.isalnum():
            validations.append('密码必须至少包含一个特殊字符')
        if validations:
            raise ValidationError(validations)
        else:
            return password

    def to_representation(self, instance):
            ret = super(UserPasswordSerializer, self).to_representation(instance)
            ret["password"] = '*****'
            return ret

    def update(self, instance, validated_data):
        password = make_password(validated_data["password"])
        instance.password = password
        instance.save()
        return instance