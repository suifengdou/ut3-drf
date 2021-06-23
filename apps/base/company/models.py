from django.db import models
import django.utils.timezone as timezone
import pandas as pd


class Company(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '正常'),
    )
    CATEGORY = (
        (0, '小狗体系'),
        (1, '物流快递'),
        (2, '仓库存储'),
        (3, '生产制造'),
        (4, '经销代理'),
        (5, '其他类型'),
    )

    name = models.CharField(unique=True, max_length=30, verbose_name='公司简称', db_index=True, help_text='公司简称')
    company = models.CharField(null=True, blank=True, max_length=60, verbose_name='公司名称', help_text='公司名称')
    tax_fil_number = models.CharField(unique=True, null=True, blank=True, max_length=30, verbose_name='税号', help_text='税号')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    category = models.IntegerField(choices=CATEGORY, default=1, verbose_name='公司类型', help_text='公司类型')
    spain_invoice = models.FloatField(null=True, blank=True, verbose_name='普票限额', help_text='普票限额')
    special_invoice = models.FloatField(null=True, blank=True, verbose_name='专票限额', help_text='专票限额')
    discount_rate = models.FloatField(default=1.0, verbose_name='折扣率', help_text='折扣率')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'BASE-公司-公司管理'
        verbose_name_plural = verbose_name
        db_table = 'base_company'

    def __str__(self):
        return self.name