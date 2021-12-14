import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import IntStatement


class IntStatementSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = IntStatement
        fields = "__all__"

    def get_ipo(self, instance):

        try:
            ret = {
                "id": instance.ipo.id,
                "order_id": instance.ipo.order_id,
                "distributor": instance.ipo.distributor.name,
                "contract_id": instance.ipo.contract_id,
                "currency": instance.ipo.currency.name,
                "amount": instance.ipo.amount,
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_receipt(self, instance):

        try:
            ret = {
                "id": instance.receipt.id,
                "bank_sn": instance.receipt.bank_sn,
                "account": instance.receipt.account.name,
                "currency": instance.receipt.currency.name,
                "amount": instance.receipt.amount,
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_account(self, instance):
        try:
            ret = {
                "id": instance.account.id,
                "name": instance.account.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):

        status_list = {
            0: "已取消",
            1: "待关联",
            2: "待结算",
            3: "已完成",
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

    def to_representation(self, instance):
        ret = super(IntStatementSerializer, self).to_representation(instance)
        ret["ipo"] = self.get_ipo(instance)
        ret["receipt"] = self.get_receipt(instance)
        ret["account"] = self.get_account(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance










