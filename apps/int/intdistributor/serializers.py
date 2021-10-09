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

    def get_salesmen(self, instance):
        salesmen = instance.salesmen.all()
        ret = []
        for selesman in salesmen:
            data = {
                "id": selesman.id,
                "name": selesman.username
            }
            ret.append(data)
        return ret

    def get_contacts(self, instance):
        contacts = instance.contacts.all()
        ret = []
        for contact in contacts:
            data = {
                "id": contact.id,
                "name": contact.name
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(IntDistributorSerializer, self).to_representation(instance)
        ret["salesmen"] = self.get_salesmen(instance)
        ret["contacts"] = self.get_contacts(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        salesmen_list = validated_data.pop("salesmen", [])
        contacts_list = validated_data.pop("contacts", [])
        instance = self.Meta.model.objects.create(**validated_data)
        instance.salesmen.set(salesmen_list)
        instance.contacts.set(contacts_list)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        salesmen_list = validated_data.pop("salesmen", [])
        contacts_list = validated_data.pop("contacts", [])
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        instance.salesmen.set(salesmen_list)
        instance.contacts.set(contacts_list)
        return instance


class ContactsSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Contacts
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(ContactsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
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










