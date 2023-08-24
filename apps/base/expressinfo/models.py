from django.db import models
from apps.base.company.models import Company
from apps.auth.users.models import UserProfile


class ExpressCategory(models.Model):
    name = models.CharField(unique=True, max_length=30, verbose_name='快递类别', help_text='快递类别')
    code = models.CharField(max_length=30, verbose_name='类别编码', help_text='类别编码')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='公司', help_text='公司')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-快递-快递类型'
        verbose_name_plural = verbose_name
        db_table = 'base_express_category'

    def __str__(self):
        return str(self.id)


class Express(models.Model):
    TYPE = (
        (1, '普通单号'),
        (2, '线下热敏'),
    )
    name = models.CharField(unique=True, max_length=30, verbose_name='快递名称', help_text='快递名称')
    code = models.CharField(unique=True, max_length=30, verbose_name='快递编码', help_text='快递编码')
    category = models.ForeignKey(ExpressCategory, on_delete=models.CASCADE, verbose_name='快递类别', help_text='快递类别')
    track_no_type = models.SmallIntegerField(choices=TYPE, default=1, verbose_name='单号类别', help_text='单号类别')

    app_key = models.CharField(max_length=90, null=True, blank=True, verbose_name='授权码', help_text='授权码')
    auth_code = models.CharField(max_length=90, null=True, blank=True, verbose_name='客户编码', help_text='客户编码')
    auth_name = models.CharField(max_length=90, null=True, blank=True, verbose_name='客户名称', help_text='客户名称')
    sign = models.CharField( max_length=90, null=True, blank=True, verbose_name='客户标识', help_text='客户标识')
    sign_1 = models.CharField(max_length=90, null=True, blank=True, verbose_name='特殊标识1', help_text='特殊标识1')
    sign_2 = models.CharField(max_length=90, null=True, blank=True, verbose_name='特殊标识2', help_text='特殊标识2')
    sign_3 = models.CharField(max_length=90, null=True, blank=True, verbose_name='特殊标识3', help_text='特殊标识3')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-快递'
        verbose_name_plural = verbose_name
        db_table = 'base_express'

    def __str__(self):
        return str(self.id)


class LogExpress(models.Model):
    obj = models.ForeignKey(Express, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'BASE-快递-日志'
        verbose_name_plural = verbose_name
        db_table = 'base_express_logging'

    def __str__(self):
        return str(self.id)






