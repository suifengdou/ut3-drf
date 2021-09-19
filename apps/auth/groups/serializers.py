import datetime
from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

class GroupSerializer(serializers.ModelSerializer):
    """
    用户组 序列化类
    """
    permission = serializers.CharField(required=False)
    class Meta:
        model = Group
        fields = "__all__"

    def get_permissions(self, instance):
        permissions = instance.permissions.all()
        ret = []
        for permission in permissions:
            data = {
                "id": permission.id,
                "name": permission.name
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(GroupSerializer, self).to_representation(instance)
        ret["users"] = instance.user_set.count()
        ret["permissions"] = self.get_permissions(instance)
        return ret

    def to_internal_value(self, data):
        print(data)
        return super(GroupSerializer, self).to_internal_value(data)


    def create(self, validated_data):
        permission_list = validated_data.pop("permissions", [])
        instance = self.Meta.model.objects.create(**validated_data)
        instance.permissions.set(permission_list)
        return instance

    def update(self, instance, validated_data):
        permission_list = validated_data.pop("permissions", [])
        user_list = validated_data.pop("users", [])
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        instance.permissions.set(permission_list)
        return instance


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = "__all__"