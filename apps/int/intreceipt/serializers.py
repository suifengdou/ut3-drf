import datetime
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import IntReceipt
from apps.int.intstatement.models import IntStatement


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
            1: "待审核",
            2: "待关联",
            3: "待结算",
            4: "已完成",
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
            1: "反馈信息为空",

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

    def to_representation(self, instance):
        ret = super(IntReceiptSerializer, self).to_representation(instance)
        ret["currency"] = self.get_currency(instance)
        ret["account"] = self.get_account(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["category"] = self.get_category(instance)
        ret["photo_details"] = self.get_photo_details(instance)
        return ret

    def get_statement_details(self, instance):
        statement_details = instance.intstatement_set.all()
        ret = []
        for statement_detail in statement_details:
            data = {
                "id": statement_detail.id,
                "goods_id": statement_detail.ipo.order_id,
                "currency": statement_detail.currency.id,
                "quantity": statement_detail.quantity,
                "price": statement_detail.price,
                "memorandum": statement_detail.memorandum
            }
            ret.append(data)
        return ret


    def check_statement_details(self, statement_details):
        for statement in statement_details:
            if not all([statement.get("goods_name", None), statement.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], statement_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")
        currency_list = list(map(lambda x: x["currency"], statement_details))
        currency_check = set(currency_list)
        if len(currency_check) != 1:
            raise serializers.ValidationError("明细中币种必须一致！")
        else:
            currency = Currency.objects.filter(id=list(currency_check)[0])[0]
        amount_list = list(map(lambda x: float(x["price"]) * int(x["quantity"]), statement_details))
        quantity_list = list(map(lambda x: int(x["quantity"]), statement_details))
        amount = reduce(lambda x, y: x + y, amount_list)
        quantity = reduce(lambda x, y: x + y, quantity_list)
        return currency, amount, quantity

    def create_statement_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            goods_detail = IntStatement.objects.create(**data)
        else:
            goods_detail = IntStatement.objects.filter(id=data["id"]).update(**data)
        return goods_detail

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
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance










