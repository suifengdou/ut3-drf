
from django.db import models
import django.utils.timezone as timezone

from apps.base.company.models import Company


class ExpressWorkOrder(models.Model):
    VERIFY_FIELD = ['express_id', 'information', 'category']
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '快递未递'),
        (2, '逆向未理'),
        (3, '正向未递'),
        (4, '快递在理'),
        (5, '复核未理'),
        (6, '终审未理'),
        (7, '财务审核'),
        (8, '工单完结'),
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
    WO_CATEGORY = (
        (0, '正向工单'),
        (1, '逆向工单'),
    )
    COMPANY = (
        (0, '申通'),
    )
    LOGICAL_DEXISION = (
        (0, '否'),
        (1, '是'),
    )
    PROCESSTAG = (
        (0, '未分类'),
        (1, '待截单'),
        (2, '签复核'),
        (3, '改地址'),
        (4, '催派查'),
        (5, '丢件核'),
        (6, '纠纷中'),
        (7, '其他'),

    )
    HANDLERS = (
        (0, '皮卡丘'),
        (1, '伊布'),
        (3, '波比克'),
    )

    express_id = models.CharField(unique=True, max_length=100, verbose_name='源单号')
    information = models.TextField(max_length=600, verbose_name='初始问题信息')
    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='客服提交时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='客服')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='客服处理间隔(分钟)')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='快递处理人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='快递处理时间')
    express_interval = models.IntegerField(null=True, blank=True, verbose_name='快递处理间隔(分钟)')
    feedback = models.TextField(null=True, blank=True, max_length=900, verbose_name='反馈内容')
    is_losing = models.BooleanField(default=False, verbose_name='是否丢件')

    return_express_id = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回单号')
    is_return = models.IntegerField(choices=LOGICAL_DEXISION, default=1, verbose_name='是否返回')
    memo = models.TextField(null=True, blank=True, verbose_name='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态')
    category = models.SmallIntegerField(choices=CATEGORY, default=0, verbose_name='工单事项类型')
    wo_category = models.SmallIntegerField(choices=WO_CATEGORY, default=0, verbose_name='工单类型')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='快递公司')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    mid_handler = models.SmallIntegerField(choices=HANDLERS, default=0, verbose_name='跟单小伙伴')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'EXT-快递工单-查询'
        verbose_name_plural = verbose_name
        db_table = 'ext_workorderex'

    def __str__(self):
        return self.express_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None