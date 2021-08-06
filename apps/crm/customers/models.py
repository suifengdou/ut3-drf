from django.db import models
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse


class Customer(models.Model):

    mobile = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='手机')

    e_mail = models.EmailField(null=True, blank=True, verbose_name='电子邮件')
    qq = models.CharField(null=True, blank=True, max_length=30, verbose_name='QQ')
    wangwang = models.CharField(null=True, blank=True, max_length=60, verbose_name='旺旺')
    jdfbp_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='京东FBP账号')
    jdzy_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='京东自营账号')
    gfsc_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='官方商城账号')
    alipay_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='支付宝账号')
    pdd_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='拼多多账号')
    wechat = models.CharField(null=True, blank=True, max_length=60, verbose_name='微信号')
    others_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='其他平台')

    birthday = models.DateTimeField(null=True, blank=True, verbose_name='生日')
    total_amount = models.FloatField(default=0, verbose_name='购买总金额')
    total_times = models.IntegerField(default=0, verbose_name='购买总次数')
    last_time = models.DateTimeField(null=True, blank=True, verbose_name='最近购买时间')

    return_time = models.DateTimeField(null=True, blank=True, verbose_name='最后一次回访时间')
    contact_times = models.IntegerField(null=True, blank=True, default=0, verbose_name='回访关怀次数')

    free_service_times = models.IntegerField(default=0, verbose_name='无金额发货次数')
    maintenance_times = models.IntegerField(default=0, verbose_name='中央维修次数')
    memorandum = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')
    order_failure_times = models.IntegerField(default=0, verbose_name='退款次数')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-C-客户信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer'

    def __str__(self):
        return str(self.mobile)








