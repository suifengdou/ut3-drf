import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import CustomerLabelPerson, LogCustomerLabelPerson, CustomerLabelFamily, LogCustomerLabelFamily, \
    CustomerLabelProduct, LogCustomerLabelProduct, CustomerLabelOrder, LogCustomerLabelOrder, CustomerLabelService, \
    LogCustomerLabelService, CustomerLabelSatisfaction, LogCustomerLabelSatisfaction, CustomerLabelRefund, \
    LogCustomerLabelRefund, CustomerLabelOthers, LogCustomerLabelOthers
from apps.utils.logging.loggings import logging


class CustomerLabelPersonSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelPerson
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelPersonSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelPerson, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelPerson, "修改内容：%s" % str(content))
        return instance


class CustomerLabelFamilySerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelFamily
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelFamilySerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelFamily, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelFamily, "修改内容：%s" % str(content))
        return instance


class CustomerLabelProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelProduct
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelProductSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelProduct, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelProduct, "修改内容：%s" % str(content))
        return instance


class CustomerLabelOrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelOrder
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelOrderSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelOrder, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelOrder, "修改内容：%s" % str(content))
        return instance


class CustomerLabelServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelService
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelServiceSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelService, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelService, "修改内容：%s" % str(content))
        return instance


class CustomerLabelSatisfactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelSatisfaction
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelSatisfactionSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelSatisfaction, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelSatisfaction, "修改内容：%s" % str(content))
        return instance


class CustomerLabelRefundSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelRefund
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelRefundSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelRefund, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelRefund, "修改内容：%s" % str(content))
        return instance


class CustomerLabelOthersSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerLabelOthers
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(CustomerLabelOthersSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogCustomerLabelOthers, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if value != check_value:
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogCustomerLabelOthers, "修改内容：%s" % str(content))
        return instance









