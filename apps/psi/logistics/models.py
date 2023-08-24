import time
import hashlib
import base64
import requests
import json
from ut3.settings import DEPPON_API
from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
from apps.base.goods.models import Goods
from apps.base.warehouse.models import Warehouse
from apps.base.expressinfo.models import Express
from apps.crm.csaddress.models import CSAddress
from apps.base.goods.models import Goods
from apps.utils.logging.loggings import logging


class Logistics(models.Model):

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '待推送'),
        (2, '已推送'),
        (3, '已完成'),
    )

    code = models.CharField(max_length=50, unique=True, verbose_name='关联单号', help_text='关联单号')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库', help_text='仓库')
    express = models.ForeignKey(Express, on_delete=models.CASCADE, verbose_name='快递公司', help_text='快递公司')
    parentMailNo = models.CharField(db_index=True, max_length=150, null=True, blank=True, verbose_name='主单号', help_text='主单号')
    mailNo = models.CharField(db_index=True, max_length=200, null=True, blank=True, verbose_name='子单号', help_text='子单号')
    fee = models.IntegerField(default=0, verbose_name='额外运费金额', help_text='额外运费金额')
    reason = models.CharField(null=True, blank=True, max_length=200, verbose_name='错误原因', help_text='错误原因')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='单据状态')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-物流快递'
        verbose_name_plural = verbose_name
        db_table = 'psi_logistics'

    def __str__(self):
        return str(self.id)

    def get_model_logistic(self, *args, **kwargs):
        customer_label_dict = {
            "DEPPON": Deppon,
        }
        model_class = customer_label_dict.get(self.express.category.code, None)

        return {"model": model_class}


class Deppon(models.Model):

    ORDERSTATUS = (
        (0, '无'),
        (1, '揽货失败'),
        (2, '正常签收'),
        (3, '已开单'),
        (4, '已受理'),
        (5, '异常签收'),
        (6, '接货中'),
        (7, '已撤销'),
        (8, '已退回'),
    )

    TYPE_DICT = {
        "标准快递": "PACKAGE",
        "大件快递360": "ORCP",
    }
    DELIVERY_TYPE = {
        (1, '自提'),
        (2, '送货进仓'),
        (3, '送货不含上楼'),
        (4, '送货上楼'),
        (5, '大件上楼'),
        (7, '送货安装'),
        (8, '送货入户'),
    }

    order = models.OneToOneField(Logistics, on_delete=models.CASCADE, verbose_name='源单', help_text='源单')
    parentMailNo = models.CharField(db_index=True, max_length=150, null=True, blank=True, verbose_name='主单号',
                                    help_text='主单号')
    logisticID = models.CharField(max_length=32, db_index=True, verbose_name='渠道单号', help_text='渠道单号')
    custOrderNo = models.CharField(max_length=32, verbose_name='客户订单号', help_text='客户订单号')
    muchHigherDelivery = models.IntegerField(default=0, verbose_name='超远派送金额', help_text='超远派送金额')
    companyCode = models.CharField(max_length=32, verbose_name='公司编码', help_text='公司编码')
    customerCode = models.CharField(max_length=32, verbose_name='月结账号', help_text='月结账号')
    orderType = models.CharField(max_length=32, verbose_name='下单模式', help_text='下单模式')
    transportType = models.CharField(max_length=32, verbose_name='产品类型', help_text='产品类型')

    sender = models.ForeignKey(CSAddress, on_delete=models.CASCADE, related_name='sender', verbose_name='发货人信息', help_text='发货人信息')
    receiver = models.ForeignKey(CSAddress, on_delete=models.CASCADE, related_name='receiver', verbose_name='发货人信息', help_text='发货人信息')

    cargoName = models.CharField(max_length=250, verbose_name='货物名称', help_text='货物名称')
    totalNumber = models.IntegerField(default=1, verbose_name='总件数', help_text='总件数')
    totalWeight = models.FloatField(default=0, verbose_name='总件数', help_text='总件数')

    deliveryType = models.IntegerField(choices=DELIVERY_TYPE, null=True, blank=True, verbose_name='送货方式', help_text='送货方式')

    gmtCommit = models.DateTimeField(null=True, blank=True, verbose_name='订单提交时间', help_text='订单提交时间')

    payType = models.CharField(max_length=32, default=3, verbose_name='支付方式', help_text='支付方式')
    smsNotify = models.CharField(max_length=32, default='Y', verbose_name='短信通知', help_text='短信通知')
    reason = models.CharField(null=True, blank=True, max_length=200, verbose_name='错误原因', help_text='错误原因')
    remark = models.CharField(null=True, blank=True, max_length=100, verbose_name='备注', help_text='备注')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=0, verbose_name='回传状态')

    is_push = models.BooleanField(default=False, verbose_name='是否推送', help_text='是否推送')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-物流快递-德邦'
        verbose_name_plural = verbose_name
        db_table = 'psi_logistics_deppon'

    def __str__(self):
        return str(self.id)

    def pushOrder(self, params, action, *args, **kwargs):
        current_time = time.time()
        time_stamp = str(int(round(current_time * 1000)))
        app_key = self.order.express.app_key
        params = json.dumps(params)
        plainText = f"{params}{app_key}{time_stamp}"
        digest = hashlib.md5(plainText.encode("utf-8")).hexdigest()
        digest = base64.b64encode(digest.encode("utf-8"))
        data = {
            "companyCode": self.order.express.auth_name,
            "digest": digest,
            "timestamp": time_stamp,
            "params": params,
        }
        headers = {"content-type": 'application/x-www-form-urlencoded'}
        try:
            result = requests.post(DEPPON_API[action], headers=headers, data=data)
            result = json.loads(result.text)
            return result
        except Exception as e:
            result = {"result": "false", "error": [f"{e}"]}
            return result

    def createOrder(self, request):
        user = request.user
        action = "CREATE_URL"
        current_time = time.time()
        gmtCommit = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
        self.gmtCommit = gmtCommit
        params = {
            "logisticID": self.logisticID,
            "custOrderNo": self.custOrderNo,
            "companyCode": self.companyCode,
            "transportType": self.transportType,
            "customerCode": self.customerCode,
            "orderType": self.orderType,
            "sender": {
                "name": self.sender.name,
                "mobile": self.sender.mobile,
                "province": self.sender.city.province.name,
                "city": self.sender.city.name,
                "county": self.sender.district.name,
                "address": self.sender.address,
            },
            "receiver": {
                "name": self.receiver.name,
                "mobile": self.receiver.mobile,
                "province": self.receiver.city.province.name,
                "city": self.receiver.city.name,
                "county": self.receiver.district.name,
                "address": self.receiver.address,
            },
            "packageInfo": {
                "cargoName": self.cargoName,
                "totalNumber": self.totalNumber,
                "totalWeight": self.totalWeight,
                "deliveryType": self.deliveryType,
            },
            "gmtCommit": gmtCommit,
            "payType": self.payType,
            "smsNotify": self.smsNotify,
        }
        result = self.pushOrder(params, action)
        if result["result"] == 'false':
            result_data = {"result": False, "error": [f"{result['reason']}"]}
            return result_data
        else:
            if "parentMailNo" in result:
                self.parentMailNo = result["parentMailNo"]
                self.order.parentMailNo = result["parentMailNo"]
                self.order.mailNo = result["mailNo"]
            else:
                self.parentMailNo = result["mailNo"]
                self.order.parentMailNo = result["mailNo"]
                self.order.mailNo = result["mailNo"]
            if "muchHigherDelivery" in result:
                self.order.fee = result["muchHigherDelivery"]
            self.remark = result["uniquerRequestNumber"]
            self.save()
            logging(self, user, LogDeppon, "获取单号成功")
            self.order.save()
            logging(self.order, user, LogLogistics, "回传单号成功")
            result_data = {"result": True, "error": [], "track_no": self.parentMailNo}
            return result_data

    def queryOrder(self, request):
        status_dict = {
            '揽货失败': 1,
            '正常签收': 2,
            '已开单': 3,
            '已受理': 4,
            '异常签收': 5,
            '接货中': 6,
            '已撤销': 7,
            '已退回': 8,
        }
        action = "QUERY_URL"
        current_time = time.time()
        gmtCommit = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
        self.gmtCommit = gmtCommit
        params = {
            "logisticCompanyID": "DEPPON",
            "logisticID": self.logisticID,
        }
        result = self.pushOrder(params, action)
        if result["result"] == 'false':
            result_data = {"result": False, "error": [f"{result['reason']}"]}
            return result_data
        else:
            if not self.parentMailNo:
                if "parentMailNo" in result["responseParam"]:
                    self.parentMailNo = result["responseParam"]["parentMailNo"]
                    self.order.parentMailNo = result["responseParam"]["parentMailNo"]
                    self.order.mailNo = result["responseParam"]["mailNo"]
                else:
                    self.parentMailNo = result["responseParam"]["mailNo"]
                    self.order.parentMailNo = result["responseParam"]["mailNo"]
                    self.order.mailNo = result["responseParam"]["mailNo"]
                    self.order.save()
            order_status = status_dict.get(result["responseParam"]["statusType"], None)
            if order_status != self.order_status:
                self.order_status = order_status
                if order_status in [1, 7, 8]:
                    self.order.order_status = 0
                    self.order.save()
                elif order_status == 2:
                    self.order.order_status = 3
                    self.order.save()
            self.save()
            result_data = {"result": True, "error": [], "track_no": self.parentMailNo, "statusType": result["responseParam"]["statusType"]}
            return result_data

    def cancelOrder(self, request):
        user = request.user
        action = "CANCEL_URL"
        current_time = time.time()
        cancelTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
        params = {
            "logisticCompanyID": "DEPPON",
            "logisticID": self.logisticID,
            "mailNo": self.parentMailNo,
            "cancelTime": cancelTime,
            "remark": "订单退款",
        }
        result = self.pushOrder(params, action)
        if result["result"] == 'false':
            result_data = {"result": False, "error": [f"{result['reason']}"]}
            return result_data
        else:
            self.order_status = 7
            self.save()
            logging(self, user, LogDeppon, "撤销成功")
            self.order.order_status = 0
            self.order.save()
            logging(self.order, user, LogLogistics, "取消成功")
            result_data = {"result": True, "error": [], "track_no": self.parentMailNo}
            return result_data

    def transferCode(self, request):
        user = request.user
        transfer_code = str(self.logisticID).split("-")
        if len(transfer_code) < 2:
            transfer_code = f"{transfer_code[0]}-1"
        else:
            number = int(transfer_code[1]) + 1
            transfer_code = f"{transfer_code[0]}-{number}"
        self.logisticID = transfer_code
        self.save()
        logging(self.order, user, LogLogistics, "更新快递详情单")


class LogLogistics(models.Model):
    obj = models.ForeignKey(Logistics, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-物流快递-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_logistics_logging'

    def __str__(self):
        return str(self.id)


class LogDeppon(models.Model):
    obj = models.ForeignKey(Deppon, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-物流快递-德邦-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_logistics_deppon_logging'

    def __str__(self):
        return str(self.id)




