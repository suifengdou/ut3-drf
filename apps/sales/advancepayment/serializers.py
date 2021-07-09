import datetime
from django.db.models import Avg,Sum,Max,Min
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Account, Statements, Prestore, Expense, VerificationPrestore, VerificationExpenses, ExpendList


class AccountSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Account
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已冻结",
            1: "正常",
        }
        ret = {
            "id": instance.order_status,
            "name": order_status.get(instance.order_status, None)
        }
        return ret

    def get_user(self, instance):
        ret = {
            "id": instance.user.id,
            "name": instance.user.username
        }
        return ret

    def get_balance(self, instance):
        all_prestores = instance.prestore_set.filter(order_status=3)
        if all_prestores:
            balance = all_prestores.aggregate(Sum("remaining"))["remaining__sum"]
        else:
            balance = 0
        return balance

    def to_representation(self, instance):
        ret = super(AccountSerializer, self).to_representation(instance)
        try:
            ret["order_status"] = self.get_order_status(instance)
            ret["user"] = self.get_user(instance)
            ret["balance"] = self.get_balance(instance)
        except:
            error = {"id": -1, "name": "显示错误"}
            ret["order_status"] = error
            ret["user"] = error
            ret["balance"] = error
        return ret

    def to_internal_value(self, data):
        return super(AccountSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class StatementsSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Statements
        fields = "__all__"

    def get_account(self, instance):
        ret = {
            "id": instance.account.id,
            "name": instance.account.name
        }
        return ret

    def get_category(self, instance):
        category = {
            0: "支出",
            1: "预存",
            2: "退款"
        }
        ret = {
            "id": instance.category,
            "name": category.get(instance.category, None)
        }
        return ret

    def to_representation(self, instance):
        ret = super(StatementsSerializer, self).to_representation(instance)
        try:
            ret["category"] = self.get_category(instance)
            ret["account"] = self.get_account(instance)
        except Exception as e:
            print(e)
            error = {"id": -1, "name": "显示错误"}
            ret["category"] = error
            ret["account"] = error
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class PrestoreSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Prestore
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "未提交",
            2: "待审核",
            3: "已入账",
            4: "已清账",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_category(self, instance):
        category = {
            0: "支出",
            1: "预存",
            2: "退款"
        }
        try:
            ret = {
                "id": instance.category,
                "name": category.get(instance.category, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_account(self, instance):
        try:
            ret = {
                "id": instance.account.id,
                "name": instance.account.name
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def to_representation(self, instance):
        ret = super(PrestoreSerializer, self).to_representation(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["category"] = self.get_category(instance)
        ret["account"] = self.get_account(instance)
        return ret

    def validate_account(self, value):
        """
        Check that the blog post is about Django.
        """
        user = self.context["request"].user
        _q_account = Account.objects.filter(user=user)
        if _q_account:
            value = _q_account[0]
        else:
            raise ValidationError("登陆账号无充值账户，无法创建预存充值！")
        return value

    def to_internal_value(self, data):
        if not data["order_id"]:
            prefix = "P"
            serial_number = str(datetime.datetime.now())
            serial_number = int(serial_number.replace("-", "").replace(" ", "").replace(":", "").replace(".", ""))
            data["order_id"] = prefix + str(serial_number)[:18]
        return super(PrestoreSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ExpenseSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Expense
        fields = "__all__"

    def get_order_status(self, instance):
        order_status = {
            0: "已取消",
            1: "待结算",
            2: "已清账",
        }
        ret = {
            "id": instance.order_status,
            "name": order_status.get(instance.order_status, None)
        }
        return ret

    def get_account(self, instance):
        ret = {
            "id": instance.account.id,
            "name": instance.account.name
        }
        return ret

    def get_category(self, instance):
        category = {
            0: "支出",
            1: "预存",
            2: "退款"
        }
        ret = {
            "id": instance.category,
            "name": category.get(instance.category, None)
        }
        return ret

    def to_representation(self, instance):
        ret = super(ExpenseSerializer, self).to_representation(instance)
        try:
            ret["account"] = self.get_account(instance)
            ret["order_status"] = self.get_order_status(instance)
            ret["category"] = self.get_category(instance)
        except:
            error = {"id": -1, "name": "显示错误"}
            ret["order_status"] = error
            ret["category"] = error
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class VerificationPrestoreSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = VerificationPrestore
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(VerificationPrestoreSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class VerificationExpensesSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = VerificationExpenses
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(VerificationExpensesSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class ExpendListSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ExpendList
        fields = "__all__"

    def get_prestore(self, instance):
        ret = {
            "id": instance.prestore.id,
            "name": instance.prestore.order_id
        }
        return ret

    def get_prestore_amount(self, instance):
        return instance.prestore.amount

    def get_account(self, instance):
        ret = {
            "id": instance.account.id,
            "name": instance.account.name
        }
        return ret

    def get_statement_expense(self, instance):
        return instance.statements.expenses

    def get_statment(self, instance):
        ret = {
            "id": instance.statements.id,
            "name": instance.statements.order_id
        }
        return ret

    def to_representation(self, instance):
        ret = super(ExpendListSerializer, self).to_representation(instance)
        ret["statements"] = self.get_statment(instance)
        ret["statment_expense"] = self.get_statement_expense(instance)
        ret["account"] = self.get_account(instance)
        ret["prestore"] = self.get_prestore(instance)
        ret["prestore_amount"] = self.get_prestore_amount(instance)
        return ret

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user.username
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["update_time"] = datetime.datetime.now()
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


