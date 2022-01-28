from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
from apps.int.intreceipt.models import IntReceipt
from apps.int.intpurchase.models import IntPurchaseOrder
from apps.int.intaccount.models import IntAccount


class IntStatement(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待关联'),
        (2, '待结算'),
        (3, '已完成'),
    )

    order_id = models.CharField(unique=True, max_length=130, db_index=True, null=True, blank=True, verbose_name='结算编号', help_text='结算编号')
    ipo = models.ForeignKey(IntPurchaseOrder, on_delete=models.CASCADE, verbose_name='采购单', help_text='采购单')
    receipt = models.ForeignKey(IntReceipt, on_delete=models.CASCADE, verbose_name='收款单', help_text='收款单')
    account = models.ForeignKey(IntAccount, on_delete=models.CASCADE, verbose_name='收款账户', help_text='收款账户')
    actual_amount = models.FloatField(default=0, verbose_name='实收金额', help_text='实收金额')
    virtual_amount = models.FloatField(default=0, verbose_name='销减金额', help_text='销减金额')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-收款结算单'
        unique_together = (("ipo", "receipt"),)
        verbose_name_plural = verbose_name
        db_table = 'int_statement'
        permissions = (
            ('view_user_intstatement', 'Can view user INT-收款结算单'),
            ('view_handler_intstatement', 'Can view handler INT-收款结算单'),
            ('view_Checker_intstatement', 'Can view Checker INT-收款结算单'),
        )

    def __str__(self):
        return self.order_id

