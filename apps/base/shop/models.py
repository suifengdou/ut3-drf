from django.db import models
from apps.base.company.models import Company

# Create your models here.
class Platform(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '正常'),
    )

    name = models.CharField(unique=True, max_length=30, verbose_name='平台名称', db_index=True, help_text='平台名称')
    category = models.CharField(null=True, blank=True, max_length=30, verbose_name='类型', db_index=True, help_text='类型')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='平台状态', help_text='平台状态')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-平台类型'
        verbose_name_plural = verbose_name
        db_table = 'base_platform'

    def __str__(self):
        return self.name


class Shop(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '正常'),
    )

    name = models.CharField(unique=True, max_length=30, verbose_name='店铺名', db_index=True, help_text='店铺名')
    shop_id = models.CharField(unique=True, max_length=30, verbose_name='店铺ID', db_index=True, null=True, blank=True, help_text='店铺ID')
    platform = models.ForeignKey(Platform, on_delete=models.SET_NULL, verbose_name='平台', null=True, blank=True, help_text='平台')
    group_name = models.CharField(max_length=30, verbose_name='店铺分组', help_text='店铺分组')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, verbose_name='公司', null=True, blank=True, help_text='公司')
    order_status = models.BooleanField(default=True, verbose_name='店铺状态', help_text='店铺状态')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-店铺'
        verbose_name_plural = verbose_name
        db_table = 'base_shop'

    def __str__(self):
        return self.name