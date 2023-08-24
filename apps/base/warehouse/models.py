from django.db import models

# Create your models here.
from apps.utils.geography.models import City, District


class WarehouseType(models.Model):
    name = models.CharField(unique=True, max_length=30, verbose_name='仓库类型', help_text='仓库类型')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-仓库类型'
        verbose_name_plural = verbose_name
        db_table = 'base_wah_category'

    def __str__(self):
        return self.name


class Warehouse(models.Model):

    name = models.CharField(unique=True, max_length=60, verbose_name='仓库名称', help_text='仓库名称')
    code = models.CharField(unique=True, max_length=20, verbose_name='仓库ID', help_text='仓库ID')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='城市地点', help_text='城市地点')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区县',
                                 help_text='区县')
    receiver = models.CharField(null=True, blank=True, max_length=50, verbose_name='收货人', help_text='收货人')
    mobile = models.CharField(null=True, blank=True, max_length=30, verbose_name='电话', help_text='电话')
    address = models.CharField(null=True, blank=True, max_length=90, verbose_name='地址', help_text='地址')
    category = models.ForeignKey(WarehouseType, on_delete=models.CASCADE, verbose_name='仓库类型', help_text='仓库类型')
    order_status = models.BooleanField(default=False, verbose_name='仓库状态', help_text='仓库状态')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-仓库'
        verbose_name_plural = verbose_name
        db_table = 'base_wah_warehouse'

    def __str__(self):
        return self.name
