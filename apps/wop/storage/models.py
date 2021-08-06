

from django.db import models
import django.utils.timezone as timezone

from apps.base.goods.models import Goods
from apps.base.company.models import Company


class StorageWorkOrder(models.Model):
    VERIFY_FIELD = ['keyword', 'information', 'category']
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '逆向未递'),
        (2, '逆向未理'),
        (3, '正向未递'),
        (4, '仓储未理'),
        (5, '复核未理'),
        (6, '财务审核'),
        (7, '工单完结'),
    )
    CATEGORY = (
        (0, '入库错误'),
        (1, '系统问题'),
        (2, '单据问题'),
        (3, '订单类别'),
        (4, '入库咨询'),
        (5, '出库咨询'),
    )
    WO_CATEGORY = (
        (0, '正向工单'),
        (1, '逆向工单'),
    )

    keyword = models.CharField(unique=True, max_length=100, verbose_name='事务关键字')
    information = models.TextField(max_length=600, verbose_name='初始问题信息')
    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='客服提交时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='客服')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='客服处理间隔(分钟)')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='供应处理人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='供应处理时间')
    express_interval = models.IntegerField(null=True, blank=True, verbose_name='供应处理间隔(分钟)')
    feedback = models.TextField(null=True, blank=True, max_length=900, verbose_name='逆向反馈内容')
    is_losing = models.BooleanField(default=False, verbose_name='是否理赔')

    return_express_id = models.CharField(null=True, blank=True, max_length=200, verbose_name='正向反馈内容')
    is_return = models.BooleanField(default=False, verbose_name='是否反馈')
    memo = models.TextField(null=True, blank=True, verbose_name='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态')
    category = models.SmallIntegerField(choices=CATEGORY, default=0, verbose_name='工单事项类型')
    wo_category = models.SmallIntegerField(choices=WO_CATEGORY, default=0, verbose_name='工单类型')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='供应商')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-仓储工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_storage'

    def __str__(self):
        return self.keyword

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None