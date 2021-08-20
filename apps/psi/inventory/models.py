from django.db import models
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods

# Create your models here.

class Inventory(models.Model):
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品')
    goods_id = models.CharField(max_length=30, verbose_name='货品编码')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库')


    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-库存管理'
        verbose_name_plural = verbose_name
        db_table = 'psi_inventory'
        unique_together = (("goods_name", "warehouse"),)

    def __str__(self):
        return self.goods_name
