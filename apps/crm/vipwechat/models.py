from django.db import models
from apps.crm.customers.models import Customer
from apps.auth.users.models import UserProfile

class Specialist(models.Model):
    username = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='客服', help_text='客服')
    name = models.CharField(max_length=150, unique=True, verbose_name='账号名', help_text='账号名')
    is_default = models.BooleanField(default=True, verbose_name='是否默认', help_text='是否默认')
    smartphone = models.CharField(max_length=150, unique=True, verbose_name='手机', help_text='手机')
    description = models.TextField(verbose_name='账号描述', help_text='账号描述')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    class Meta:
        verbose_name = 'CRM-VIP-微信服务-专属客服'
        verbose_name_plural = verbose_name
        db_table = 'crm_vipwebchat_specialist'

    def __str__(self):
        return str(self.id)


class VIPWechat(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待确认'),
        (2, '确认完成'),
    )
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, verbose_name='服务账号', help_text='服务账号')
    cs_wechat = models.CharField(unique=True, max_length=150, verbose_name='客户微信', help_text='客户微信')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', help_text='单据状态')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-VIP-微信服务'
        verbose_name_plural = verbose_name
        db_table = 'crm_vipwebchat'

    def __str__(self):
        return str(self.id)


    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["customer", "specialist", "cs_wechat", "memo"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None

