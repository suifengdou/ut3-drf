from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
from apps.int.intaccount.models import IntAccount, Currency


class IntReceipt(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
        (4, '已清账'),
    )
    CATEGORY = (
        (1, '预存'),
        (2, '退款'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '流水号重复'),
        (2, '反馈信息为空'),
    )

    order_id = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='回单编号', help_text='回单编号')
    account = models.ForeignKey(IntAccount, on_delete=models.CASCADE, verbose_name='关联账户', help_text='关联账户')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name='币种', help_text='币种')
    bank_sn = models.CharField(unique=True, max_length=100, verbose_name='交易流水号', help_text='交易流水号')
    category = models.IntegerField(choices=CATEGORY, default=1, verbose_name='类型', help_text='类型')

    amount = models.FloatField(default=0, verbose_name='存入金额', help_text='存入金额')
    remaining = models.FloatField(default=0, verbose_name='可拆金额', help_text='可拆金额')
    memorandum = models.CharField(max_length=200, verbose_name='备注', help_text='备注')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    feedback = models.CharField(max_length=150, blank=True, null=True, verbose_name='反馈内容', help_text='反馈内容')

    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-预付-预存管理'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_prestore'
        permissions = (
            ('view_user_prestore', 'Can view user SALES-预付-预存管理'),
        )

    def __str__(self):
        return self.order_id








