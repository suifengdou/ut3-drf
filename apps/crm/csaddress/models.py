from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.utils.geography.models import Province, City, District
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from apps.crm.customers.models import Customer


class CSAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='用户', help_text='用户')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='城市', help_text='城市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区县', help_text='区县')
    name = models.CharField(max_length=150, verbose_name='收件人', help_text='收件人')
    mobile = models.CharField(max_length=50, db_index=True, verbose_name='手机', help_text='手机')
    address = models.CharField(max_length=250, verbose_name='地址', help_text='地址')
    is_default = models.BooleanField(default=False, verbose_name='是否默认', help_text='是否默认')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    class Meta:
        verbose_name = 'CRM-CSADDRESS-收件信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_csaddress'

    def __str__(self):
        return str(self.id)


class LogCSAddress(models.Model):
    obj = models.ForeignKey(CSAddress, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CSADDRESS-收件信息-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_csaddress_logging'

    def __str__(self):
        return str(self.id)
