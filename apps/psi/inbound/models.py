from django.db import models
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods


# Create your models here.

class OriInbound(models.Model):

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '已完成的入库单则无法递交'),
        (2, '系统无此仓库'),
        (3, '系统无此货品'),
        (4, '类别错误'),
        (5, '此入库单合并仓库不一致'),
        (6, '此入库单合并类别不一致'),
        (7, '重复递交'),
        (8, '保存出错'),
        (9, '明细重复递交'),
        (10, '明细保存出错'),
        (11, '仓库未设置监控'),
    )

    STATUS_LIST = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '已提交'),
    )

    order_id = models.CharField(max_length=50, verbose_name='入库单号')
    ori_order_status = models.CharField(max_length=50, verbose_name='状态')
    category = models.CharField(max_length=50, verbose_name='类别')
    ori_order_id = models.CharField(max_length=50, verbose_name='源单号')
    warehouse = models.CharField(max_length=50, verbose_name='仓库')
    handler = models.CharField(max_length=50, verbose_name='经办人')
    goods_id = models.CharField(max_length=50, verbose_name='商家编码')
    goods_name = models.CharField(max_length=90, verbose_name='货品名称')
    quantity = models.CharField(max_length=50, verbose_name='调整后数量')
    created_time = models.DateTimeField(verbose_name='建单时间')
    handle_time = models.DateTimeField(verbose_name='审核入库时间')
    memorandum = models.CharField(null=True, blank=True, max_length=150, verbose_name='备注')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    order_status = models.IntegerField(choices=STATUS_LIST, default=1, verbose_name='单据状态')

    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-原始库单'
        verbose_name_plural = verbose_name
        db_table = 'psi_inbound_ori'
        unique_together = (("order_id", "goods_id"),)

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["order_id", "ori_order_status", "category", "ori_order_id",
                        "warehouse", "handler", "goods_id", "goods_name", "quantity",
                        "create_time", "handle_time", "memorandum"]
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class Inbound(models.Model):

    STATUS_LIST = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
    )

    CATEGORY_LIST = (
        (1, '采购入库'),
        (2, '调拨入库'),
        (3, '退货入库'),
        (4, '生产入库'),
        (5, '保修入库'),
        (6, '其他入库'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '递交重复'),
        (2, '保存出错'),
        (3, '仓库非法'),
    )

    order_id = models.CharField(max_length=50, unique=True, verbose_name='入库单号', help_text='入库单号')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,  verbose_name='仓库', help_text='仓库')
    category = models.IntegerField(choices=CATEGORY_LIST, default=1,  verbose_name='类别', help_text='类别')
    memorandum = models.CharField(null=True, blank=True, max_length=150, verbose_name='备注', help_text='备注')
    volume = models.FloatField(null=True, blank=True, verbose_name='体积', help_text='体积')
    weight = models.FloatField(null=True, blank=True, verbose_name='重量', help_text='重量')
    order_status = models.IntegerField(choices=STATUS_LIST, default=1, verbose_name='单据状态', help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-入库单'
        verbose_name_plural = verbose_name
        db_table = 'psi_inbound'

    def __str__(self):
        return str(self.id)


class InboundDetail(models.Model):

    STATUS_LIST = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
        (4, '已清账'),
    )

    order = models.ForeignKey(Inbound, on_delete=models.CASCADE, verbose_name='入库单', help_text='入库单')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库', help_text='仓库')
    quantity = models.IntegerField(verbose_name='入库数量', help_text='入库数量')
    valid_quantity = models.IntegerField(default=0, verbose_name='可用数量', help_text='可用数量')
    froze_quantity = models.IntegerField(default=0, verbose_name='冻结数量', help_text='冻结数量')
    memo = models.CharField(null=True, blank=True, max_length=150, verbose_name='备注', help_text='备注')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核入库时间', help_text='审核入库时间')

    order_status = models.IntegerField(choices=STATUS_LIST, default=1, verbose_name='单据状态', help_text='单据状态')
    is_complelted = models.BooleanField(default=False, verbose_name='入库标记', help_text='入库标记')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-入库单明细'
        verbose_name_plural = verbose_name
        db_table = 'psi_inbound_detail'
        unique_together = (("order", "goods_name"),)

    def __str__(self):
        return str(self.id)


class InboundVerify(models.Model):
    ori_inbound = models.OneToOneField(OriInbound, on_delete=models.CASCADE, verbose_name='原始入库单', help_text='原始入库单')
    inbound_detail = models.OneToOneField(InboundDetail, on_delete=models.CASCADE, verbose_name='入库单', help_text='入库单')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-入库单明细'
        verbose_name_plural = verbose_name
        db_table = 'psi_inbound_verify'

    def __str__(self):
        return str(self.id)



