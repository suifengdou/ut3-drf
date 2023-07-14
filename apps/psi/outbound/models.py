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

    code = models.CharField(max_length=50, unique=True, verbose_name='出库单号', help_text='出库单号')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库')
    verification = models.CharField(db_index=True, max_length=150, verbose_name='验证号', help_text='验证号')
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
        return self.code


class OutboundDetail(models.Model):

    STATUS_LIST = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
        (4, '已清账'),
    )
    CATEGORY_LIST = (
        (1, '正品'),
        (2, '残品'),
    )

    order = models.ForeignKey(Outbound, on_delete=models.CASCADE, verbose_name='出库单', help_text='出库单')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    code = models.CharField(max_length=90, db_index=True, verbose_name='出库货品单号', help_text='出库货品单号')
    category = models.IntegerField(choices=CATEGORY_LIST, default=1, verbose_name='货品类型', help_text='货品类型')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库', help_text='仓库')
    quantity = models.IntegerField(verbose_name='出库数量', help_text='出库数量')

    price = models.IntegerField(default=0, verbose_name='价格', help_text='价格')
    memo = models.CharField(null=True, blank=True, max_length=150, verbose_name='备注', help_text='备注')

    order_status = models.IntegerField(choices=STATUS_LIST, default=1, verbose_name='单据状态', help_text='单据状态')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核出库时间', help_text='审核出库时间')
    is_complelted = models.BooleanField(default=False, verbose_name='出库标记', help_text='出库标记')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-出库管理-货品'
        verbose_name_plural = verbose_name
        db_table = 'psi_outbound_detail'
        unique_together = (("order", "goods"),)

    def __str__(self):
        return str(self.id)


class LogOutbound(models.Model):
    obj = models.ForeignKey(Outbound, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-出库管理-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_outbound_logging'

    def __str__(self):
        return str(self.id)


class LogOutboundDetail(models.Model):
    obj = models.ForeignKey(OutboundDetail, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-出库管理-货品-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_outbound_detail_logging'

    def __str__(self):
        return str(self.id)





