from django.db import models
from apps.base.warehouse.models import Warehouse



class Prestore(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
        (4, '已清账'),
    )
    CATEGORY = (
        (1, '预存'),
        (2, '退款'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '流水号重复'),
        (2, '反馈信息为空'),
        (3, '预存不可重复审核'),
        (4, '保存流水出错'),
        (5, '保存验证出错'),
    )

    order_id = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='预存号', help_text='预存号')
    account = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='入库仓库')
    bank_sn = models.CharField(unique=True, max_length=100, verbose_name='流水号', help_text='流水号')
    category = models.IntegerField(choices=CATEGORY, default=1, verbose_name='类型', help_text='类型')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    amount = models.FloatField(default=0, verbose_name='存入金额', help_text='存入金额')
    remaining = models.FloatField(default=0, verbose_name='可用金额', help_text='可用金额')
    memorandum = models.CharField(max_length=200, verbose_name='备注', help_text='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    feedback = models.CharField(max_length=150, blank=True, null=True, verbose_name='反馈内容', help_text='反馈内容')

    class Meta:
        verbose_name = 'SALES-预付-预存管理'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_prestore'
        permissions = (
            ('view_user_prestore', 'Can view user SALES-预付-预存管理'),
            ('view_handler_prestore', 'Can view handler SALES-预付-预存管理'),
        )

    def __str__(self):
        return self.order_id