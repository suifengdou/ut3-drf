from django.db import models
from apps.base.company.models import Company
from apps.utils.geography.models import Nationality
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.int.intdistributor.models import IntDistributor
from apps.int.intaccount.models import Currency, IntAccount


# Create your models here.
class IntPurchaseOrder(models.Model):

    CATEGORY_LIST = (
        (1, '样机'),
        (2, '批量'),
    )

    MODE_LIST = (
        (1, 'FOB'),
        (2, 'CIF'),
        (3, 'EXW'),
        (4, 'DDP'),
    )


    po_id = models.CharField(unique=True, max_length=200, db_index=True, verbose_name='采购单号', help_text='采购单号')
    distributor = models.ForeignKey(IntDistributor, on_delete=models.CASCADE, verbose_name='经销商', help_text='经销商')
    order_category = models.SmallIntegerField(choices=CATEGORY_LIST, default=1, verbose_name='类型', help_text='类型')

    account = models.ForeignKey(IntAccount, on_delete=models.CASCADE, verbose_name='收款账户', help_text='收款账户')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name='币种', help_text='币种')

    trade_mode = models.SmallIntegerField(choices=CATEGORY_LIST, default=1, verbose_name='贸易方式', help_text='贸易方式')

    amount = models.FloatField(default=0, verbose_name='采购单总金额', help_text='采购单总金额')
    deposit = models.FloatField(default=0, verbose_name='定金', help_text='定金')


    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际经销商-联系人'
        verbose_name_plural = verbose_name
        db_table = 'int_distributor_contacts'

    def __str__(self):
        return self.name