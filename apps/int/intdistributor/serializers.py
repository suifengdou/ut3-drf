import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import IntDistributor, Contacts, ContactMode


class IntDistributorSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = IntDistributor
        fields = "__all__"

    def get_category(self, instance):
        category_list = {
            1: "商业",
            2: "终端",
            3: "全渠道",
        }
        try:
            ret = {
                "id": instance.category,
                "name": category_list.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        status_list = {
            1: "已取消",
            2: "正常",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status_list.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_nationality(self, instance):
        try:
            ret = {
                "id": instance.nationality.id,
                "name": instance.nationality.name
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

    def to_representation(self, instance):
        ret = super(IntDistributorSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["nationality"] = self.get_nationality(instance)
        ret["department"] = self.get_department(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        validated_data["department"] = user.department
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ContactsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Contacts
        fields = "__all__"

    def get_contact_details(self, instance):
        contact_details = instance.contactmode_set.all()
        ret = []
        for contact_detail in contact_details:
            data = {
                "id": contact_detail.id,
                "name": contact_detail.name,
                "content": contact_detail.content
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(ContactsSerializer, self).to_representation(instance)
        ret["contact_details"] = self.get_contact_details(instance)
        return ret

    def create_contact_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            contact_detail = ContactMode.objects.create(**data)
        else:
            data.pop("name", None)
            id = data.pop("id", None)
            contact_detail = ContactMode.objects.filter(id=id).update(**data)
        return contact_detail

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        contact_details = validated_data.pop("contact_details", [])
        instance = self.Meta.model.objects.create(**validated_data)
        for contact_detail in contact_details:
            contact_detail['contacts'] = instance
            contact_detail.pop("xh")
            self.create_contact_detail(contact_detail)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        contact_details = validated_data.pop("contact_details", [])
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        if contact_details:
            instance.contactmode_set.all().delete()
            for contact_detail in contact_details:
                contact_detail['contacts'] = instance
                contact_detail.pop("xh")
                self.create_contact_detail(contact_detail)
        return instance


class ContactModeSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ContactMode
        fields = "__all__"

    def get_contacts(self, instance):
        try:
            ret = {
                "id": instance.contacts.id,
                "name": instance.contacts.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(ContactModeSerializer, self).to_representation(instance)
        ret["contacts"] = self.get_contacts(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance










