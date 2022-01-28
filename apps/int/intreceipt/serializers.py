import datetime
from functools import reduce
from django.db.models import Q, Count, Sum, Max, Min, Avg
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import IntReceipt
from apps.int.intstatement.models import IntStatement
from apps.int.intaccount.models import Currency


class IntReceiptSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    statement_details = serializers.JSONField(required=False)

    class Meta:
        model = IntReceipt
        fields = "__all__"

    def get_currency(self, instance):

        try:
            ret = {
                "id": instance.currency.id,
                "name": instance.currency.name
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
                "name": instance.account.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):

        status_list = {
            0: "已取消",
            1: "待提交",
            2: "待认领",
            3: "待审核",
            4: "待关联",
            5: "待结算",
            6: "已完成",
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

    def get_mistake_tag(self, instance):

        mistake_list = {
            0: "正常",
            1: "流水号重复",
            2: "收款金额为零",
            3: "收款单未认领",
            4: "非认领人不可审核",
            5: "未到账不可审核",

        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_category(self, instance):

        category_list = {
            1: "存入",
            2: "支出",

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

    def get_photo_details(self, instance):
        photo_details = instance.irphoto_set.all()
        ret = []
        for photo_detail in photo_details:
            data = {
                "id": photo_detail.id,
                "name": photo_detail.url,
            }
            ret.append(data)
        return ret

    def get_statement_details(self, instance):
        statement_details = instance.intstatement_set.all()
        ret = []
        for statement_detail in statement_details:
            data = {
                "id": statement_detail.id,
                "ipo": {
                    "id": statement_detail.ipo.id,
                    "name": statement_detail.ipo.order_id,
                },
                "actual_amount": statement_detail.actual_amount,
                "virtual_amount": statement_detail.virtual_amount,
                "memorandum": statement_detail.memorandum
            }
            ret.append(data)
        return ret

    def get_associated_amount(self, instance):
        statement_details = instance.intstatement_set.filter(order_status=1)
        try:
            associated_amount = statement_details.aggregate(Sum("actual_amount"))["actual_amount__sum"]
        except Exception as e:
            associated_amount = 0
        if not associated_amount:
            associated_amount = 0
        return associated_amount

    def to_representation(self, instance):
        ret = super(IntReceiptSerializer, self).to_representation(instance)
        ret["currency"] = self.get_currency(instance)
        ret["account"] = self.get_account(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["category"] = self.get_category(instance)
        ret["photo_details"] = self.get_photo_details(instance)
        ret["statement_details"] = self.get_statement_details(instance)
        ret["associated_amount"] = self.get_associated_amount(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        number = int(instance.id) + 10000000
        profix = "COD"
        instance.order_id = '%s%s' % (profix, str(number)[-7:])
        instance.save()
        return instance

    def update(self, instance, validated_data):
        statement_details = validated_data.pop("statement_details", [])
        associated_amount = validated_data.pop("associated_amount", 0)
        photo_details = validated_data.pop("photo_details", [])
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance










