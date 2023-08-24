import datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Renovation, RenovationGoods, Renovationdetail, LogRenovation, LogRenovationGoods, LogRenovationdetail, ROFiles
from apps.utils.logging.loggings import getlogs, logging
from apps.base.goods.models import Goods, Bom
from apps.psi.inbound.models import Inbound


class RenovationSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Renovation
        fields = "__all__"

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "返回单号为空",
            2: "处理意见为空",
            3: "经销商反馈为空",
            4: "创建出库单明细出错",
            5: "存在配件出库明细不可以取消",
            6: "非特殊无配件不可审核",
            7: "关联出库单错误，联系管理员",
            8: "关联出库单创建错误",
            9: "未锁定单据不可审核",
            10: "未锁定单据不可设置特殊标记",
            11: "已出库单据不可重复出库",
            12: "库存不存在",
            13: "缺货无法出库",
            14: "出库单据未出库配件",
            15: "出库单据未出库残品",
            16: "出库单据已存在正品入库单",
            17: "已操作出库单据无法驳回",
            18: "出库数量错误",
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

    def get_order_status(self, instance):
        status_list = {
            0: "已取消",
            1: "待翻新",
            2: "待入库",
            3: "已完结",
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

    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.code
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_warehouse(self, instance):
        try:
            ret = {
                "id": instance.warehouse.id,
                "name": instance.warehouse.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(RenovationSerializer, self).to_representation(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order"] = self.get_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["warehouse"] = self.get_warehouse(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        if "verification" not in validated_data:
            raise ValidationError({"创建错误": "没有验证号"})
        else:
            validated_data["verification"] = validated_data["verification"].replace(" ", "")
            _q_inbound = Inbound.objects.filter(verification=validated_data["verification"])
            if _q_inbound.exists():
                inbound = _q_inbound[0]
                all_inbound_goods = inbound.inbounddetail_set.all()
                if len(all_inbound_goods) == 1:
                    inbound_goods = all_inbound_goods[0]
                    if inbound_goods.category != 2 or inbound_goods.valid_quantity == 0:
                        raise ValidationError({"创建错误": "关联多货品不存在或者类型非残品！"})
                else:
                    if "goods" not in validated_data:
                        raise ValidationError({"创建错误": "关联多货品入库单，货品项必填！"})
                    _q_inbound_goods = all_inbound_goods.filter(goods=validated_data["goods"])
                    if _q_inbound_goods.exists():
                        inbound_goods = _q_inbound_goods[0]
                    else:
                        raise ValidationError({"创建错误": "关联入库单未找到翻新货品！"})
            else:
                raise ValidationError({"创建错误": "没有找到入库单！"})

        validated_data["order"] = inbound_goods
        validated_data["goods"] = inbound_goods.goods
        validated_data["warehouse"] = inbound_goods.warehouse
        validated_data["code"] = inbound_goods.code
        instance = self.Meta.model.objects.create(**validated_data)
        instance.code = f"{instance.code}-{instance.id}"
        logging(instance, user, LogRenovation, "创建")
        _q_parts_bom = Bom.objects.filter(goods=instance.goods, is_delete=0)
        if _q_parts_bom.exists():
            for part_obj in _q_parts_bom:
                renovation_detail_dict = {
                    "order": instance,
                    "goods": part_obj.part,
                    "creator": user.username,
                }
                renovation_detail = Renovationdetail.objects.create(**renovation_detail_dict)
                logging(renovation_detail, user, LogRenovationdetail, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        if "order" in validated_data:
            if validated_data["order"] != instance.order:
                if validated_data["order"].category == 1:
                    raise ValidationError({"更新错误": "关联入库单必须是残品！"})
                if validated_data["order"].valid_quantity == 0:
                    raise ValidationError({"更新错误": "关联入库单可用库存为零！"})
                validated_data["goods"] = validated_data["order"].goods
                validated_data["warehouse"] = validated_data["order"].warehouse
                validated_data["code"] = f"{validated_data['order'].code}-{instance.id}"

        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovation, "修改内容：%s" % str(content))
        return instance


class RenovationGoodsSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = RenovationGoods
        fields = "__all__"

    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.code,
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
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
            1: "无货品不可审核",
            2: "保存出错",
            3: "仓库非法",
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

    def get_order_status(self, instance):
        order_status = {
            1: "待处理",
            2: "已确认",
            3: "待清账",
            4: "已处理"
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": order_status.get(instance.order_status, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(RenovationGoodsSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogRenovationGoods, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovationGoods, "修改内容：%s" % str(content))
        return instance


class RenovationdetailSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = Renovationdetail
        fields = "__all__"

    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.code
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_goods(self, instance):
        try:
            ret = {
                "id": instance.goods.id,
                "name": instance.goods.name
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
            1: "未提交",
            2: "待审核",
            3: "已入账",
            4: "已清账"
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
        ret = super(RenovationdetailSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["goods"] = self.get_goods(instance)
        ret["order_status"] = self.get_order_status(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance, user, LogRenovationdetail, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance, user, LogRenovationdetail, "修改内容：%s" % str(content))
        return instance


class ROFilesSerializer(serializers.ModelSerializer):

    created_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    updated_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = ROFiles
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(RenovationGoodsSerializer, self).to_representation(instance)
        return ret

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = self.context["request"].user.username
        instance = self.Meta.model.objects.create(**validated_data)
        logging(instance.workorder, user, LogRenovation, "创建")
        return instance

    def update(self, instance, validated_data):
        user = self.context["request"].user
        validated_data["updated_time"] = datetime.datetime.now()
        # 改动内容
        content = []
        for key, value in validated_data.items():
            if 'time' not in str(key):
                check_value = getattr(instance, key, None)
                if str(value) != str(check_value):
                    content.append('{%s}:%s 替换 %s' % (key, value, check_value))

        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        logging(instance.workorder, user, LogRenovation, "修改内容：%s" % str(content))
        return instance












