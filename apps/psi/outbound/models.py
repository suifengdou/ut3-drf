from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
from apps.base.goods.models import Goods
from apps.base.warehouse.models import Warehouse
from apps.base.shop.models import Shop


class Outbound(models.Model):

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '递交重复'),
        (2, '保存出错'),
        (3, '仓库非法'),
    )

    ob_order_id = models.CharField(max_length=30, verbose_name='出库编号')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺')
    goods_id = models.CharField(max_length=30, verbose_name='商家编码')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品')
    quantity = models.IntegerField(verbose_name='实发数量')
    deliver_time = models.CharField(max_length=30, verbose_name='发货时间')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-出库管理'
        verbose_name_plural = verbose_name
        db_table = 'psi_outbound'

    def __str__(self):
        return self.ob_order_id