
from django.db import models
import django.utils.timezone as timezone

from apps.base.company.models import Company
from apps.base.goods.models import Goods


class DealerWorkOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待递交'),
        (2, '等待处理'),
        (3, '等待执行'),
        (4, '等待确认'),
        (5, '工单完结'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '已处理'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '返回单号或快递为空'),
        (2, '处理意见为空'),
        (3, '执行内容为空'),
        (4, '驳回原因为空'),
        (5, '先标记为已处理才能审核'),

    )

    WO_CATEGORY = (
        (1, '退货'),
        (2, '换货'),
        (3, '维修'),
    )


    order_id = models.CharField(unique=True, max_length=100, verbose_name='源订单单号', help_text='源订单单号')
    information = models.TextField(max_length=600, verbose_name='初始问题信息', help_text='初始问题信息')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name='公司', help_text='公司')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    quantity = models.IntegerField(verbose_name='数量', help_text='数量')
    amount = models.FloatField(verbose_name='合计金额', help_text='合计金额')
    category = models.SmallIntegerField(choices=WO_CATEGORY, default=1, verbose_name='单据类型', help_text='单据类型')
    is_customer_post = models.BooleanField(default=False, verbose_name='是否客户邮寄', help_text='是否客户邮寄')
    return_express_company = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回快递公司', help_text='返回快递公司')
    return_express_id = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回单号', help_text='返回单号')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间', help_text='处理时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='处理人', help_text='处理人')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='处理间隔(分钟)', help_text='处理间隔(分钟)')
    is_losing = models.BooleanField(default=False, verbose_name='是否丢件', help_text='是否丢件')
    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(null=True, blank=True, max_length=260, verbose_name='驳回原因', help_text='驳回原因')

    feedback = models.TextField(null=True, blank=True, max_length=900, verbose_name='执行内容', help_text='执行内容')
    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='执行人', help_text='执行人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='执行时间', help_text='执行时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='执行间隔(分钟)', help_text='执行间隔(分钟)')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')
    memo = models.TextField(null=True, blank=True, verbose_name='备注', help_text='备注')

    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-经销商工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_dealer'

        permissions = (
            # (权限，权限描述),
            ('view_user_dealerworkorder', 'Can view user WOP-经销商工单-用户'),
            ('view_handler_dealerworkorder', 'Can view handler WOP-经销商工单-处理'),
            ('view_check_dealerworkorder', 'Can view check WOP-经销商工单-审核'),
            ('view_audit_dealerworkorder', 'Can view audit WOP-经销商工单-结算'),
        )

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['order_id', 'information', 'category']
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None