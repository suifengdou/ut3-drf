
from django.db import models
import django.utils.timezone as timezone

from apps.base.company.models import Company
from apps.base.goods.models import Goods


class ExpressWorkOrder(models.Model):
    VERIFY_FIELD = ['express_id', 'information', 'category']
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '创建未递'),
        (2, '等待处理'),
        (3, '等待执行'),
        (4, '终审复核'),
        (5, '财务审核'),
        (6, '工单完结')
    )
    CATEGORY = (
        (0, '截单退回'),
        (1, '无人收货'),
        (2, '客户拒签'),
        (3, '修改地址'),
        (4, '催件派送'),
        (5, '虚假签收'),
        (6, '丢件破损'),
        (7, '其他异常'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '快递单号错误'),
        (2, '处理意见为空'),
        (3, '返回的单据无返回单号'),
        (4, '理赔必须设置需理赔才可以审核'),
        (5, '驳回原因为空'),
        (6, '无反馈内容, 不可以审核'),
    )

    PROCESSTAG = (
        (0, '未分类'),
        (1, '待截单'),
        (2, '签复核'),
        (3, '改地址'),
        (4, '催派查'),
        (5, '丢件核'),
        (6, '纠纷中'),
        (7, '需理赔'),
        (8, '其他类'),

    )
    HANDLINGS = (
        (0, '未处理'),
        (1, '在处理'),
        (2, '待核实'),
        (3, '已处理'),
    )

    track_id = models.CharField(unique=True, max_length=100, verbose_name='快递单号', help_text='快递单号')
    category = models.SmallIntegerField(choices=CATEGORY, default=0, verbose_name='工单事项类型', help_text='工单事项类型')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='快递公司', help_text='快递公司')
    information = models.TextField(max_length=600, verbose_name='初始问题信息', help_text='初始问题信息')
    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间', help_text='处理时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='处理人', help_text='处理人')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='处理间隔(分钟)', help_text='处理间隔(分钟)')
    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(null=True, blank=True, max_length=260, verbose_name='驳回原因', help_text='驳回原因')
    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='执行人', help_text='执行人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='执行时间', help_text='执行时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='执行间隔(分钟)', help_text='执行间隔(分钟)')
    feedback = models.TextField(null=True, blank=True, max_length=900, verbose_name='执行内容', help_text='执行内容')
    is_losing = models.BooleanField(default=False, verbose_name='是否理赔', help_text='是否理赔')

    return_express_id = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回单号', help_text='返回单号')
    is_return = models.BooleanField(default=False, verbose_name='是否返回', help_text='是否返回')
    memo = models.TextField(null=True, blank=True, verbose_name='备注', help_text='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')

    is_forward = models.BooleanField(default=False, verbose_name='是否正向', help_text='是否正向')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    handling_status = models.SmallIntegerField(choices=HANDLINGS, default=0, verbose_name='处理状态', help_text='处理状态')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-快递工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_express'

        permissions = (
            # (权限，权限描述),
            ('view_user_expressworkorder', 'Can view user WOP-快递工单-用户'),
            ('view_handler_expressworkorder', 'Can view handler WOP-快递工单-处理'),
            ('view_check_expressworkorder', 'Can view check WOP-快递工单-审核'),
            ('view_audit_expressworkorder', 'Can view audit WOP-快递工单-结算'),
        )

    def __str__(self):
        return self.id

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None

