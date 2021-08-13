from django.db import models
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse


class Customer(models.Model):

    mobile = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='手机')
    memorandum = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')


    class Meta:
        verbose_name = 'CRM-C-客户信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer'

    def __str__(self):
        return str(self.mobile)








