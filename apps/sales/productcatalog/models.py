from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd
from apps.base.goods.models import Goods
from apps.base.department.models import Department
from apps.base.company.models import Company


class ProductCatalog(models.Model):
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='部门', help_text='部门')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='经销商', help_text='经销商')
    price = models.IntegerField(default=0, verbose_name='销售单价', help_text='销售单价')
    memo = models.CharField(max_length=230, null=True, blank=True, verbose_name='备注', help_text='备注')
    order_status = models.BooleanField(default=False, verbose_name='状态', help_text='状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-销售列表'
        verbose_name_plural = verbose_name
        db_table = 'sales_product_catalog'
        unique_together = (("company", "goods"), )
        permissions = (
            ('view_user_productcatalog', 'Can view user SALES-销售列表'),
        )

    def __str__(self):
        return self.goods.name

