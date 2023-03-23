from django.db import models
from apps.base.company.models import Company
from apps.utils.geography.models import Nationality
from django.contrib.auth import get_user_model
User = get_user_model()


class Currency(models.Model):
    name = models.CharField(max_length=90, unique=True, db_index=True, verbose_name='货币名称', help_text='货币名称')
    abbreviation = models.CharField(max_length=90, verbose_name='英文缩写', help_text='英文缩写')
    symbol = models.CharField(null=True, blank=True, max_length=90, verbose_name='符号', help_text='符号')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际账户-币种'
        verbose_name_plural = verbose_name
        db_table = 'int_account_currency'


    def __str__(self):
        return self.name


# Create your models here.
class IntAccount(models.Model):

    name = models.CharField(unique=True, max_length=200, db_index=True, verbose_name='账户名称', help_text='账户名称')
    a_id = models.CharField(null=True, blank=True, max_length=90, verbose_name='账户ID', help_text='账户ID')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name='币种', help_text='币种')
    branch = models.CharField(max_length=200, verbose_name='开户行', help_text='开户行')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='开户公司', help_text='开户公司')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际账户'
        verbose_name_plural = verbose_name
        db_table = 'int_account'

    def __str__(self):
        return self.name










