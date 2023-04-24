from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.utils.geography.models import Province, City, District
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from apps.crm.customers.models import Customer


class CSGoods(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='用户', help_text='用户')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='机器', help_text='机器')
    sn = models.CharField(max_length=50, verbose_name='sn', help_text='sn')
    purchase_time = models.DateTimeField(verbose_name='购买时间', help_text='购买时间')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    class Meta:
        verbose_name = 'CRM-CSGOODS-货品'
        verbose_name_plural = verbose_name
        db_table = 'crm_csgoods'

    def __str__(self):
        return str(self.id)


class LogCSGoods(models.Model):
    obj = models.ForeignKey(CSGoods, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CSGOODS-收件信息-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_csgoods_logging'

    def __str__(self):
        return str(self.id)


