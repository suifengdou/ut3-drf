import datetime
import re
from functools import reduce
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import OriSatisfactionWorkOrder, OSWOFiles, SatisfactionWorkOrder, SWOProgress, SWOPFiles, ServiceWorkOrder, InvoiceWorkOrder , IWOGoods
from apps.base.goods.models import Goods
from apps.base.department.models import Department
from apps.utils.geography.tools import PickOutAdress



class OriSatisfactionWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OriSatisfactionWorkOrder
        fields = "__all__"

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_category(self, instance):
        CATEGORY_LIST = {
            1: "超期退货",
            2: "超期换货",
            3: "过保维修",
            4: "升级投诉",
            5: "其他",
        }
        try:
            ret = {
                "id": instance.category,
                "name": CATEGORY_LIST.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "等待递交",
            2: "递交完成",
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

    def get_process_tag(self, instance):
        process_tag = {
            1: "初始提交",
            2: "处理初期",
            3: "处理后期",
            4: "处理结束",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
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
            1: "重复提交，点击修复工单",
            2: "已存在未完结工单，联系处理同学追加问题",
            3: "地址无法提取省市区",
            4: "创建体验单错误",
            5: "初始化体验单失败",
            6: "初始化体验单资料失败",
            7: "体验单已操作无法修复",

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

    def get_file_details(self, instance):
        file_details = instance.oswofiles_set.all()
        ret = []
        for file_detail in file_details:
            if file_detail.suffix in ['png', 'jpg', 'gif', 'bmp', 'tif', 'svg', 'raw']:
                is_pic = True
            else:
                is_pic = False
            data = {
                "id": file_detail.id,
                "name": file_detail.name,
                "suffix": file_detail.suffix,
                "url": file_detail.url,
                "url_list": [file_detail.url],
                "is_pic": is_pic
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(OriSatisfactionWorkOrderSerializer, self).to_representation(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["category"] = self.get_category(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["file_details"] = self.get_file_details(instance)
        return ret

    def to_internal_value(self, data):
        return super(OriSatisfactionWorkOrderSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        if validated_data["category"] == 0:
            raise serializers.ValidationError("未选类型，不可创建！")
        CATEGORY_LIST = {
            1: "超期退货",
            2: "超期换货",
            3: "过保维修",
            4: "升级投诉",
            5: "其他",
        }
        user = self.context["request"].user
        validated_data["creator"] = user.username
        today = datetime.datetime.now()
        validated_data["purchase_interval"] = (today - validated_data["purchase_time"]).days
        instance = self.Meta.model.objects.create(**validated_data)
        today = re.sub('[- :\.]', '', str(today))[:8]
        number = int(instance.id) + 10000000
        profix = "SWO"
        instance.order_id = '%s%s%s' % (today, profix, str(number)[-7:])
        instance.title = '%s-%s-%s' % (str(instance.nickname), str(CATEGORY_LIST.get(instance.category, None)), str(instance.demand))
        instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        return instance


class OSWOFilesSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = OSWOFiles
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(OSWOFilesSerializer, self).to_representation(instance)
        return ret

    def to_internal_value(self, data):
        return super(OSWOFilesSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        return instance


class SWOSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    progress_details = serializers.JSONField(required=False)

    class Meta:
        model = SatisfactionWorkOrder
        fields = "__all__"

    def get_category(self, instance):
        CATEGORY_LIST = {
            1: "超期退货",
            2: "超期换货",
            3: "过保维修",
            4: "升级投诉",
            5: "其他",
        }
        try:
            ret = {
                "id": instance.category,
                "name": CATEGORY_LIST.get(instance.category, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_specialist(self, instance):
        try:
            ret = {
                "id": instance.specialist.id,
                "name": instance.specialist.name
            }
        except:
            ret = {
                "id": "",
                "name": "空"
            }
        return ret

    def get_goods_name(self, instance):
        try:
            ret = {
                "id": instance.goods_name.id,
                "name": instance.goods_name.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_province(self, instance):
        try:
            ret = {
                "id": instance.province.id,
                "name": instance.province.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.district.id,
                "name": instance.district.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_cs_level(self, instance):
        level_list = {
            1: "优质",
            2: "合格",
            3: "缺陷",
        }
        try:
            ret = {
                "id": instance.cs_level,
                "name": level_list.get(instance.cs_level, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "等待递交",
            2: "等待处理",
            3: "等待审核",
            4: "等待确认",
            5: "事务完结",
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

    def get_process_tag(self, instance):
        process_tag = {
            0: "无",
            1: "近30天内重复",
            2: "近30天外重复",
            3: "存在服务单",
            4: "存在专属客服",
            5: "特殊工单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_stage(self, instance):
        stage_tag = {
            1: "初始提交",
            2: "处理初期",
            3: "处理中期",
            4: "处理后期",
            5: "处理结束",
        }
        try:
            ret = {
                "id": instance.stage,
                "name": stage_tag.get(instance.stage, None)
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
            1: "已存在已执行服务单，不可创建",
            2: "创建服务单错误",
            3: "体验单未完成不可审核",
            4: "体验单无体验指数",
            5: "创建客户体验指数错误",
            6: "单据未评价不可审核",
            7: "申诉内容为空",
            8: "工单已终审无法驳回",
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

    def get_file_details(self, progress):
        file_details = progress.swopfiles_set.all()
        ret = []
        for file_detail in file_details:
            if file_detail.suffix in ['png', 'jpg', 'gif', 'bmp', 'tif', 'svg', 'raw']:
                is_pic = True
            else:
                is_pic = False
            data = {
                "id": file_detail.id,
                "name": file_detail.name,
                "suffix": file_detail.suffix,
                "url": file_detail.url,
                "url_list": [file_detail.url],
                "is_pic": is_pic
            }
            ret.append(data)
        return ret

    def get_progress_details(self, instance):
        progress_details = instance.swoprogress_set.all()
        ret = []
        for progress_detail in progress_details:
            data = {
                "id": progress_detail.id,
                "process_id": progress_detail.process_id,
                "title": progress_detail.title,
                "stage": progress_detail.stage,
                "action": progress_detail.action,
                "content": progress_detail.content,
                "appointment": progress_detail.appointment,
                "memo": progress_detail.memo,
                "creator": progress_detail.creator,
                "create_time": progress_detail.create_time,
                "file_details": self.get_file_details(progress_detail)
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(SWOSerializer, self).to_representation(instance)
        ret["category"] = self.get_category(instance)
        ret["customer"] = self.get_customer(instance)
        ret["specialist"] = self.get_specialist(instance)
        ret["goods_name"] = self.get_goods_name(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["stage"] = self.get_stage(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["cs_level"] = self.get_cs_level(instance)
        ret["progress_details"] = self.get_progress_details(instance)
        return ret

    def to_internal_value(self, data):
        return super(SWOSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        today = datetime.datetime.now()
        validated_data["purchase_interval"] = (today - validated_data["purchase_time"]).days
        instance = self.Meta.model.objects.create(**validated_data)

        today = re.sub('[- :\.]', '', str(today))[:8]
        number = int(instance.id) + 10000000
        profix = "SWO"
        instance.order_id = '%s%s%s' % (today, profix, str(number)[-7:])
        instance.save()

        return instance

    def update(self, instance, validated_data):
        create_time = validated_data.pop("create_time", "")
        validated_data["updated_time"] = datetime.datetime.now()
        try:
            is_solved = validated_data["is_solved"]
        except:
            is_solved = instance.is_solved
        try:
            is_beaten = validated_data["is_beaten"]
        except:
            is_beaten = instance.is_beaten
        try:
            is_satisfied = validated_data["is_satisfied"]
        except:
            is_satisfied = instance.is_satisfied
        if None not in [is_solved, is_beaten, is_satisfied]:
            if not is_solved:
                validated_data["cs_level"] = 3
            else:
                if all((is_beaten, is_satisfied)):
                    validated_data["cs_level"] = 1
                else:
                    if any((is_beaten, is_satisfied)):
                        validated_data["cs_level"] = 2
                    else:
                        validated_data["cs_level"] = 3
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class SWOProgressSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = SWOProgress
        fields = "__all__"


    def get_order(self, instance):
        try:
            ret = {
                "id": instance.order.id,
                "name": instance.order.order_id
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "等待递交",
            2: "递交完成",
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

    def get_stage(self, instance):
        stage_tag = {
            1: "初始提交",
            2: "处理初期",
            3: "处理中期",
            4: "处理后期",
            5: "处理结束",
        }
        try:
            ret = {
                "id": instance.stage,
                "name": stage_tag.get(instance.stage, None)
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def to_representation(self, instance):
        ret = super(SWOProgressSerializer, self).to_representation(instance)
        ret["order"] = self.get_order(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["stage"] = self.get_stage(instance)
        return ret

    def to_internal_value(self, data):
        return super(SWOProgressSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        today = datetime.datetime.now()
        today = re.sub('[- :\.]', '', str(today))[:8]
        number = int(instance.id) + 10000000
        profix = "SWOP"
        instance.process_id = '%s%s%s' % (today, profix, str(number)[-7:])
        instance.order.stage = instance.stage
        instance.order.appointment = instance.appointment
        instance.order.save()
        instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        user = self.context["request"].user
        if instance.creator != user.username:
            raise serializers.ValidationError({"权限错误": "只有创建人才可以修改"})
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


class SWOPFilesSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")

    class Meta:
        model = SWOPFiles
        fields = "__all__"

    def to_representation(self, instance):
        ret = super(SWOPFilesSerializer, self).to_representation(instance)
        return ret

    def to_internal_value(self, data):
        return super(SWOPFilesSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        return instance


class ServiceWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    progress_details = serializers.JSONField(required=False)
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = ServiceWorkOrder
        fields = "__all__"

    def get_swo_order(self, instance):
        try:
            ret = {
                "id": instance.swo_order.id,
                "name": instance.swo_order.order_id
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_province(self, instance):
        try:
            ret = {
                "id": instance.province.id,
                "name": instance.province.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.district.id,
                "name": instance.district.name
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_order_status(self, instance):
        order_status = {
            0: "已被取消",
            1: "服务执行",
            2: "服务完成",
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

    def get_process_tag(self, instance):
        process_tag = {
            0: "无",
            1: "近30天内重复",
            2: "近30天外重复",
            3: "存在服务单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_tag.get(instance.process_tag, None)
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
            1: "存在未完结发货单",
            2: "费用为零不可审核",
            3: "不存在费用单不可以审核",
            4: "创建体验单错误",
            5: "初始化体验单失败",
            6: "初始化体验单资料失败",
            7: "体验单已操作无法修复",

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

    def to_representation(self, instance):
        ret = super(ServiceWorkOrderSerializer, self).to_representation(instance)
        ret["swo_order"] = self.get_swo_order(instance)
        ret["customer"] = self.get_customer(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        return ret

    def to_internal_value(self, data):
        return super(ServiceWorkOrderSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["creator"] = user.username
        instance = self.Meta.model.objects.create(**validated_data)
        today = datetime.datetime.now()
        today = re.sub('[- :\.]', '', str(today))[:8]
        number = int(instance.id) + 10000000
        profix = "SS"
        instance.order_id = '%s%s%s' % (profix, today, str(number)[-7:])
        instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["updated_time"] = datetime.datetime.now()
        create_time = validated_data.pop("create_time", "")
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)

        return instance


class InvoiceWorkOrderSerializer(serializers.ModelSerializer):

    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="创建时间", help_text="创建时间")
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True, label="更新时间", help_text="更新时间")
    goods_details = serializers.JSONField(required=False)

    class Meta:
        model = InvoiceWorkOrder
        fields = "__all__"


    def get_swo_order(self, instance):
        try:
            ret = {
                "id": instance.swo_order.id,
                "name": instance.swo_order.order_id
            }
        except:
            ret = {
                "id": -1,
                "name": "空"
            }
        return ret

    def get_customer(self, instance):
        try:
            ret = {
                "id": instance.customer.id,
                "name": instance.customer.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_province(self, instance):
        try:
            ret = {
                "id": instance.province.id,
                "name": instance.province.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_city(self, instance):
        try:
            ret = {
                "id": instance.city.id,
                "name": instance.city.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_district(self, instance):
        try:
            ret = {
                "id": instance.district.id,
                "name": instance.district.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_department(self, instance):
        try:
            ret = {
                "id": instance.department.id,
                "name": instance.department.name,
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_order_status(self, instance):
        status = {
            0: "已被取消",
            1: "等待递交",
            2: "等待审核",
            3: "递交成功",
        }
        try:
            ret = {
                "id": instance.order_status,
                "name": status.get(instance.order_status, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_mistake_tag(self, instance):
        mistake_list = {
            0: "正常",
            1: "电话错误",
            2: "无收件人",
            3: "地址无法提取省市区",
            4: "无UT单号",
            5: "已存在已发货订单",
            6: "创建手工单出错",
            7: "创建手工单货品出错",
            8: "无货品不可审核",
            9: "不可重复递交",
        }
        try:
            ret = {
                "id": instance.mistake_tag,
                "name": mistake_list.get(instance.mistake_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_process_tag(self, instance):
        process_list = {
            0: "未处理",
            1: "已处理",
            2: "驳回",
            3: "特殊订单",
        }
        try:
            ret = {
                "id": instance.process_tag,
                "name": process_list.get(instance.process_tag, None)
            }
        except:
            ret = {"id": -1, "name": "显示错误"}
        return ret

    def get_goods_details(self, instance):
        goods_details = instance.iwogoods_set.all()
        ret = []
        for goods_detail in goods_details:
            data = {
                "id": goods_detail.id,
                "category": goods_detail.category,
                "goods_id": goods_detail.goods_id,
                "name": {
                    "id": goods_detail.goods_name.id,
                    "name": goods_detail.goods_name.name
                },
                "quantity": goods_detail.quantity,
                "price": goods_detail.price,
                "memorandum": goods_detail.memorandum
            }
            ret.append(data)
        return ret

    def to_representation(self, instance):
        ret = super(InvoiceWorkOrderSerializer, self).to_representation(instance)
        ret["customer"] = self.get_customer(instance)
        ret["province"] = self.get_province(instance)
        ret["city"] = self.get_city(instance)
        ret["district"] = self.get_district(instance)
        ret["department"] = self.get_department(instance)
        ret["mistake_tag"] = self.get_mistake_tag(instance)
        ret["process_tag"] = self.get_process_tag(instance)
        ret["order_status"] = self.get_order_status(instance)
        ret["goods_details"] = self.get_goods_details(instance)
        return ret


    def to_internal_value(self, data):
        return super(InvoiceWorkOrderSerializer, self).to_internal_value(data)

    def check_goods_details(self, goods_details):
        for goods in goods_details:
            if not all([goods.get("goods_name", None), goods.get("quantity", None)]):
                raise serializers.ValidationError("明细中货品名称、数量和价格为必填项！")
        goods_list = list(map(lambda x: x["goods_name"], goods_details))
        goods_check = set(goods_list)
        if len(goods_list) != len(goods_check):
            raise serializers.ValidationError("明细中货品重复！")

    def create_goods_detail(self, data):
        data["creator"] = self.context["request"].user.username
        if data["id"] == 'n':
            data.pop("id", None)
            data.pop("name", None)
            goods_detail = IWOGoods.objects.create(**data)
        else:
            data.pop("name", None)
            goods_detail = IWOGoods.objects.filter(id=data["id"]).update(**data)
        return goods_detail

    def create(self, validated_data):
        today = datetime.datetime.now()
        if validated_data["swo_order"].expiration_date:
            check_date = validated_data["swo_order"].expiration_date
            if (check_date - today).days < 0:
                raise serializers.ValidationError("服务单已过期！")
        else:
            raise serializers.ValidationError("无失效时间，不可创建！")
        user = self.context["request"].user
        validated_data["creator"] = user.username

        goods_details = validated_data.pop("goods_details", [])
        self.check_goods_details(goods_details)
        department = Department.objects.filter(name="服务中心-管理")[0]
        validated_data["department"] = department
        validated_data["order_id"] = validated_data["swo_order"].order_id

        _spilt_addr = PickOutAdress(validated_data["address"])
        _rt_addr = _spilt_addr.pickout_addr()
        if not isinstance(_rt_addr, dict):
            raise serializers.ValidationError("地址无法提取省市区")
        cs_info_fields = ["province", "city", "district", "address"]
        for key_word in cs_info_fields:
            validated_data[key_word] = _rt_addr.get(key_word, None)

        invoice = self.Meta.model.objects.create(**validated_data)

        today = re.sub('[- :\.]', '', str(today))[:8]
        number = int(invoice.id) + 10000000
        profix = "SSPI"
        invoice.erp_order_id = '%s%s%s' % (profix, today, str(number)[-7:])
        invoice.save()
        for goods_detail in goods_details:
            goods_detail['invoice'] = invoice
            goods_name = Goods.objects.filter(id=goods_detail["goods_name"])[0]
            goods_detail["goods_name"] = goods_name
            goods_detail["goods_id"] = goods_name.goods_id
            goods_detail.pop("xh")
            self.create_goods_detail(goods_detail)
        all_goods_details = invoice.iwogoods_set.all()
        goods_expense = all_goods_details.filter(category__in=[1, 3])
        if goods_expense.exists():
            expense_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_expense)))
            expense = reduce(lambda x, y: x + y, expense_list)
        else:
            expense = 0
        goods_revenue = all_goods_details.filter(category__in=[2, 4])
        if goods_revenue.exists():
            revenue_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_revenue)))
            revenue = reduce(lambda x, y: x + y, revenue_list)
        else:
            revenue = 0
        invoice.cost = round(float(expense) - float(revenue), 2)
        quantity_list = list(map(lambda x: int(x.quantity), list(all_goods_details)))
        invoice.quantity = reduce(lambda x, y: x + y, quantity_list)
        invoice.save()
        return invoice

    def update(self, instance, validated_data):
        user = self.context["request"].user
        department = Department.objects.filter(name="服务中心-管理")[0]
        validated_data["department"] = department

        validated_data["updated_time"] = datetime.datetime.now()
        address = validated_data.get("address", None)
        if address:
            _spilt_addr = PickOutAdress(address)
            _rt_addr = _spilt_addr.pickout_addr()
            if not isinstance(_rt_addr, dict):
                raise serializers.ValidationError("地址无法提取省市区")
            cs_info_fields = ["province", "city", "district", "address"]
            for key_word in cs_info_fields:
                validated_data[key_word] = _rt_addr.get(key_word, None)
            if '集运' in str(validated_data["address"]):
                if validated_data["process_tag"] != 3:
                    raise serializers.ValidationError("地址是集运仓")

        goods_details = validated_data.pop("goods_details", [])
        if goods_details:
            self.check_goods_details(goods_details)
        if goods_details:
            instance.iwogoods_set.all().delete()
            for goods_detail in goods_details:
                goods_detail['invoice'] = instance
                _q_goods = Goods.objects.filter(id=goods_detail["goods_name"])[0]
                goods_detail["goods_name"] = _q_goods
                goods_detail["goods_id"] = _q_goods.goods_id
                goods_detail["id"] = 'n'
                goods_detail.pop("xh")
                self.create_goods_detail(goods_detail)

        all_goods_details = instance.iwogoods_set.all()
        goods_expense = all_goods_details.filter(category__in=[1, 3])
        if goods_expense.exists():
            expense_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_expense)))
            expense = reduce(lambda x, y: x + y, expense_list)
        else:
            expense = 0
        goods_revenue = all_goods_details.filter(category__in=[2, 4])
        if goods_revenue.exists():
            revenue_list = list(map(lambda x: float(x.price) * int(x.quantity), list(goods_revenue)))
            revenue = reduce(lambda x, y: x + y, revenue_list)
        else:
            revenue = 0
        validated_data["cost"] = round(float(expense) - float(revenue), 2)
        quantity_list = list(map(lambda x: int(x.quantity), all_goods_details))
        validated_data["quantity"] = reduce(lambda x, y: x + y, quantity_list)
        self.Meta.model.objects.filter(id=instance.id).update(**validated_data)
        return instance


