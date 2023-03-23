from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
from apps.int.intaccount.models import IntAccount, Currency

class IntReceipt(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待提交'),
        (2, '待认领'),
        (3, '待审核'),
        (4, '待关联'),
        (5, '待结算'),
        (6, '已完成'),
    )
    CATEGORY = (
        (1, '存入'),
        (2, '支出'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '流水号重复'),
        (2, '收款金额为零'),
        (3, '收款单未认领'),
        (4, '非认领人不可审核'),
        (5, '未到账不可审核'),
        (6, '可分配金额有余额'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )

    order_id = models.CharField(unique=True, max_length=130, db_index=True, null=True, blank=True, verbose_name='回单编号', help_text='回单编号')
    payment_account = models.CharField(max_length=230, db_index=True, verbose_name='付款账户', help_text='付款账户')
    payment_account_id = models.CharField(null=True, blank=True, max_length=230, db_index=True, verbose_name='付款账户ID', help_text='付款账户ID')
    account = models.ForeignKey(IntAccount, on_delete=models.CASCADE, verbose_name='收款账户', help_text='收款账户')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name='币种', help_text='币种')
    bank_sn = models.CharField(max_length=200, verbose_name='交易流水号', help_text='交易流水号')
    category = models.IntegerField(choices=CATEGORY, default=1, verbose_name='类型', help_text='类型')
    trade_time = models.DateTimeField(null=True, blank=True, verbose_name='交易日期', help_text='交易日期')
    amount = models.FloatField(default=0, verbose_name='存入金额', help_text='存入金额')
    is_received = models.BooleanField(default=False, verbose_name='是否到账', help_text='是否到账')
    remaining = models.FloatField(default=0, verbose_name='可拆金额', help_text='可拆金额')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    information = models.CharField(null=True, blank=True, max_length=200, verbose_name='信息说明', help_text='信息说明')
    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(max_length=150, blank=True, null=True, verbose_name='反馈内容', help_text='反馈内容')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='认领人', help_text='认领人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='认领时间', help_text='认领时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='认领间隔(分钟)', help_text='认领间隔(分钟)')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')

    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-收款单'
        verbose_name_plural = verbose_name
        unique_together = (("bank_sn", "account"),)
        db_table = 'int_receipt'
        permissions = (
            ('view_user_intreceipt', 'Can view user INT-收款单'),
            ('view_handler_intreceipt', 'Can view handler INT-收款单'),
            ('view_Checker_intreceipt', 'Can view Checker INT-收款单'),
        )

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["bank_sn", "account", "trade_time", "currency", "amount", "payment_account_id",
                        "payment_account", "memorandum"]
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class IRPhoto(models.Model):

    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(IntReceipt, on_delete=models.CASCADE, verbose_name='收款单', help_text='收款单')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-收款单-图片'
        verbose_name_plural = verbose_name
        db_table = 'int_receipt_photo'

    def __str__(self):
        return str(self.id)





