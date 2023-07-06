from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.department.models import Department
from apps.utils.geography.models import Province, City, District
from apps.base.warehouse.models import Warehouse
from apps.psi.inbound.models import InboundDetail
from apps.dfc.manualorder.models import MOGoods


# 尾货售后单
class RefundManualOrder(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待递交'),
        (2, '待处理'),
        (3, '待结算'),
        (4, '已完成'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待核实'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
        (5, '部分到货'),
        (6, '已到货'),
        (7, '换货'),
        (8, '驳回'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '退换数量超出原单数量'),
        (2, '退换金额超出原单金额'),
        (3, '无退货原因'),
        (4, '无返回快递单号'),
        (5, '已存在关联入库，不可以驳回'),
    )

    CATEGORY = (
        (1, '退货退款'),
        (2, '换货退回'),
        (3, '仅退款'),
    )

    ori_order = models.OneToOneField(MOGoods, on_delete=models.CASCADE, verbose_name='来源单号')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺')
    order_id = models.CharField(unique=True, max_length=100, null=True, blank=True, verbose_name='退换单号', db_index=True)
    order_category = models.SmallIntegerField(choices=CATEGORY, default=1, verbose_name='退款类型')

    receiver = models.CharField(null=True, blank=True, max_length=150, verbose_name='收件人')
    mobile = models.CharField(null=True, blank=True, max_length=30, verbose_name='手机')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    address = models.CharField(null=True, blank=True, max_length=200, verbose_name='地址')

    quantity = models.IntegerField(null=True, blank=True, verbose_name='货品总数')

    amount = models.FloatField(default=0, verbose_name='申请退款总额')
    ori_amount = models.FloatField(null=True, blank=True, verbose_name='源订单总额')

    receipted_quantity = models.IntegerField(default=0, verbose_name='到货总数')
    receipted_amount = models.FloatField(default=0, verbose_name='到货退款总额')

    track_no = models.CharField(max_length=150, null=True, blank=True, verbose_name='返回快递信息')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='退款处理时间')

    message = models.TextField(null=True, blank=True, verbose_name='工单留言')
    feedback = models.TextField(null=True, blank=True, verbose_name='工单反馈')

    info_refund = models.TextField(null=True, blank=True, verbose_name='退换货信息原因')

    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='订单状态')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-试用-退货单'
        verbose_name_plural = verbose_name
        db_table = 'sales_trialgoods_refund'
        permissions = (
            ('view_user_refundmanualorder',  'Can view user SALES-试用-退货单'),
            ('view_handler_refundmanualorder', 'Can view handler SALES-试用-退货单'),
            ('view_check_refundmanualorder', 'Can view check SALES-试用-退货单'),
        )

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['order_id', 'information', 'category']
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


# 尾货退款订单货品明细
class RMOGoods(models.Model):
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待处理'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '入库数量是0'),
        (2, '入库数和待收货数不符'),
        (3, '入库单未确认'),
        (4, '退款单未完整入库'),
    )
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待递交'),
        (2, '待入库'),
        (3, '部分到货'),
        (4, '已到货'),
    )
    order = models.OneToOneField(RefundManualOrder, on_delete=models.CASCADE, verbose_name='退款单')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.IntegerField(verbose_name='退换货数量')
    receipted_quantity = models.IntegerField(default=0, verbose_name='到货数量')
    settlement_price = models.FloatField(verbose_name='结算单价')
    settlement_amount = models.FloatField(verbose_name='货品结算总价')

    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='物流公司', help_text='物流公司')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流单号', help_text='物流单号')
    sub_trade_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='原始子单号', help_text='原始子单号')
    invoice_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='ERP单号', help_text='ERP单号')

    sn = models.CharField(null=True, blank=True, max_length=60, verbose_name='SN码', help_text='SN码')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='到货状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-试用-退货单-货品明细'
        verbose_name_plural = verbose_name
        db_table = 'sales_trialgoods_refund_goods'

    def __str__(self):
        return str(self.id)


class LogRefundManualOrder(models.Model):
    obj = models.ForeignKey(RefundManualOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'SALES-试用-退货单-日志'
        verbose_name_plural = verbose_name
        db_table = 'sales_trialgoods_refund_logging'

    def __str__(self):
        return str(self.id)


class LogRMOGoods(models.Model):
    obj = models.ForeignKey(RMOGoods, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'SALES-试用-退货单-货品明细-日志'
        verbose_name_plural = verbose_name
        db_table = 'sales_trialgoods_refund_goods_logging'

    def __str__(self):
        return str(self.id)






