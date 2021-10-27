

from django.db import models
import django.utils.timezone as timezone

from apps.base.goods.models import Goods
from apps.base.company.models import Company
from apps.base.goods.models import Goods


class StorageWorkOrder(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '工单待递'),
        (2, '工单待理'),
        (3, '工单待定'),
        (4, '财务审核'),
        (5, '工单完结'),
    )
    CATEGORY = (
        (1, '常规工作'),
        (2, '入库问题'),
        (3, '出库问题'),
        (4, '单据问题'),
        (5, '工厂问题'),
        (6, '快递问题'),
        (7, '信息咨询'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '无处理意见, 不可审核'),
        (2, '无驳回原因, 不可驳回'),
        (3, '无执行内容，不可审核'),
    )

    HANDLINGS = (
        (0, '未处理'),
        (1, '已处理'),
    )


    keyword = models.CharField(unique=True, max_length=100, verbose_name='事务关键字', help_text='事务关键字')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='公司', help_text='公司')
    information = models.TextField(max_length=600, verbose_name='初始问题信息', help_text='初始问题信息')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间', help_text='处理时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='处理人', help_text='处理人')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='处理间隔(分钟)', help_text='处理间隔(分钟)')
    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(null=True, blank=True, max_length=260, verbose_name='驳回原因', help_text='驳回原因')
    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='执行人', help_text='执行人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='执行时间', help_text='执行时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='执行间隔(分钟)', help_text='执行间隔(分钟)')
    feedback = models.CharField(null=True, blank=True, max_length=200, verbose_name='执行内容', help_text='执行内容')
    is_losing = models.BooleanField(default=False, verbose_name='是否理赔', help_text='是否理赔')
    indemnification = models.FloatField(default=0, verbose_name='理赔金额', help_text='理赔金额')

    memo = models.TextField(null=True, blank=True, verbose_name='备注', help_text='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')
    category = models.SmallIntegerField(choices=CATEGORY, default=0, verbose_name='工单事项类型', help_text='工单事项类型')
    is_forward = models.BooleanField(default=False, verbose_name='是否正向', help_text='是否正向')
    handling_status = models.SmallIntegerField(choices=HANDLINGS, default=0, verbose_name='处理状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-仓储工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_storage'
        permissions = (
            # (权限，权限描述),
            ('view_user_storageworkorder', 'Can view user WOP-仓储工单-用户'),
            ('view_handler_storageworkorder', 'Can view handler WOP-仓储工单-处理'),
            ('view_check_storageworkorder', 'Can view check WOP-仓储工单-审核'),
            ('view_audit_storageworkorder', 'Can view audit WOP-仓储工单-结算'),
        )


    def __str__(self):
        return self.keyword

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['keyword', 'company', 'information', 'category', 'memo']

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None