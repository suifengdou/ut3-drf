
from django.db import models
import django.utils.timezone as timezone

from apps.base.company.models import Company
from apps.base.goods.models import Goods


class DealerWorkOrder(models.Model):
    VERIFY_FIELD = ['order_id', 'information', 'category']
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '经销未递'),
        (2, '客服在理'),
        (3, '经销复核'),
        (4, '运营对账'),
        (5, '工单完结'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '处理中'),
        (2, '已在途'),
        (3, '收异常'),
        (4, '未退回'),
        (5, '丢件核'),
        (6, '已处理'),
        (7, '终端清'),
        (8, '已对账'),

    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '返回单号为空'),
        (2, '处理意见为空'),
        (3, '经销商反馈为空'),
        (4, '先标记为已处理才能审核'),
        (5, '先标记为已对账才能审核'),
        (6, '工单必须为取消状态'),
        (7, '先标记为终端清才能审核'),
    )

    WO_CATEGORY = (
        (0, '退货'),
        (1, '换货'),
        (2, '维修'),
    )

    PLATFORM = (
        (0, '无'),
        (1, '淘系'),
        (2, '非淘'),
    )

    order_id = models.CharField(unique=True, max_length=100, verbose_name='源订单单号')
    information = models.TextField(max_length=600, verbose_name='初始问题信息')
    memo = models.TextField(null=True, blank=True, verbose_name='经销商反馈')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='机器型号')
    quantity = models.IntegerField(verbose_name='数量')
    amount = models.FloatField(verbose_name='合计金额')
    wo_category = models.SmallIntegerField(choices=WO_CATEGORY, default=0, verbose_name='工单类型')
    is_customer_post = models.BooleanField(default=False, verbose_name='是否客户邮寄')
    return_express_company = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回快递公司')
    return_express_id = models.CharField(null=True, blank=True, max_length=100, verbose_name='返回单号')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='客服提交时间')
    servicer = models.CharField(null=True, blank=True, max_length=60, verbose_name='客服')
    services_interval = models.IntegerField(null=True, blank=True, verbose_name='客服处理间隔(分钟)')
    is_losing = models.BooleanField(default=False, verbose_name='是否丢件')
    feedback = models.TextField(null=True, blank=True, max_length=900, verbose_name='客服处理意见')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='经销商处理人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='经销商处理时间')
    express_interval = models.IntegerField(null=True, blank=True, verbose_name='经销商处理间隔(分钟)')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态')

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='dealer', verbose_name='经销商')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    platform = models.SmallIntegerField(choices=PLATFORM, default=0, verbose_name='平台')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-经销商工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_dealer'

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None