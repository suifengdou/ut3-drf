from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.utils.geography.models import Province, City, District
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile


class Customer(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='会员名')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    class Meta:
        verbose_name = 'CRM-C-客户信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer'

    def __str__(self):
        return str(self.name)


class LogCustomer(models.Model):
    obj = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-C-客户信息-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_logging'

    def __str__(self):
        return str(self.id)









