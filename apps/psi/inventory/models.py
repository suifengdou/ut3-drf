from django.db import models
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.psi.inbound.models import InboundDetail
from apps.psi.outbound.models import OutboundDetail


class Inventory(models.Model):
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品')
    goods_id = models.CharField(max_length=30, db_index=True, verbose_name='货品编码')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-库存管理'
        verbose_name_plural = verbose_name
        db_table = 'psi_inventory'
        unique_together = (("goods_name", "warehouse"),)

    def __str__(self):
        return str(self.id)


class IORelation(models.Model):
    CATEGORY_LIST = (
        (1, '正品'),
        (2, '残品'),
    )
    inbound = models.ForeignKey(InboundDetail, on_delete=models.CASCADE, verbose_name='入库单')
    outbound = models.OneToOneField(OutboundDetail, on_delete=models.CASCADE, verbose_name='出库单')
    category = models.IntegerField(choices=CATEGORY_LIST, default=1, verbose_name='货品类型', help_text='货品类型')
    quantity = models.IntegerField(default=0, verbose_name="数量", help_text="数量")

    class Meta:
        verbose_name = 'PSI-库存管理-出入库约束'
        verbose_name_plural = verbose_name
        db_table = 'psi_inventory_iorelation'

    def __str__(self):
        return str(self.id)


