from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.department.models import Department
from apps.utils.geography.models import Province, City, District


class ManualOrder(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )

    ORDER_CATEGORY = (
        (1, '质量问题'),
        (2, '开箱即损'),
        (3, '礼品赠品'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '货品名称错误'),
        (2, '14天内重复订单'),
        (3, '14天外重复订单'),
        (4, '省市区出错'),
        (5, '输出单保存出错'),
        (6, '同名订单'),
        (7, '手机错误'),
        (8, '集运仓地址'),
        (9, '无店铺'),
        (10, '售后配件需要补全sn、部件和描述')
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )

    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺名称')
    nickname = models.CharField(max_length=50, verbose_name='网名')
    receiver = models.CharField(max_length=50, verbose_name='收件人')
    address = models.CharField(max_length=250, verbose_name='地址')
    mobile = models.CharField(max_length=50, verbose_name='手机')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    order_id = models.CharField(null=True, blank=True, max_length=50, verbose_name='订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='赠品单状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人')
    order_category = models.SmallIntegerField(choices=ORDER_CATEGORY, default=3, verbose_name='单据类型')

    m_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='机器序列号')
    broken_part = models.CharField(null=True, blank=True, max_length=50, verbose_name='故障部位')
    description = models.CharField(null=True, blank=True, max_length=200, verbose_name='故障描述')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name='部门')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder'

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["shop", "nickname", "receiver", "address", "mobile", "goods_id", "quantity",
                        "order_category", "m_sn", "broken_part", "description"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class MOGoods(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未发货'),
        (2, '已发货'),
    )

    manual_order = models.ForeignKey(ManualOrder, on_delete=models.CASCADE, verbose_name='原始尾货订单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True)
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.FloatField(default=0, verbose_name='单价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='货品状态')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单-货品明细'
        verbose_name_plural = verbose_name
        unique_together = (('manual_order', 'goods_name'))
        db_table = 'dfc_manualorder_goods'

    def __str__(self):
        return self.goods_name


class ManualOrderExport(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺名称')
    nickname = models.CharField(max_length=50, verbose_name='网名')
    receiver = models.CharField(max_length=50, verbose_name='收件人')
    address = models.CharField(max_length=250, verbose_name='地址')
    mobile = models.CharField(max_length=50, verbose_name='手机')

    d_condition = models.CharField(max_length=20, default="款到发货", verbose_name='发货条件')
    discount = models.SmallIntegerField(default=0, verbose_name='优惠金额')
    post_fee = models.SmallIntegerField(default=0, verbose_name='邮费')
    receivable = models.SmallIntegerField(default=0, verbose_name='应收合计')
    goods_price = models.SmallIntegerField(default=0, verbose_name='货品价格')
    total_prices = models.SmallIntegerField(default=0, verbose_name='货品总价')

    goods_id = models.CharField(max_length=50, verbose_name='商家编码')
    goods_name = models.CharField(max_length=50, verbose_name='货品名称')
    quantity = models.SmallIntegerField(verbose_name='货品数量')

    category = models.CharField(max_length=20, default="线下零售", verbose_name='订单类别')
    buyer_remark = models.CharField(max_length=300, verbose_name='买家备注')
    cs_memoranda = models.CharField(max_length=300, verbose_name='客服备注')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    order_id = models.CharField(null=True, blank=True, max_length=50, db_index=True, verbose_name='订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='赠品单状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人')
    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单ERP格式导出'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder_export'

    def __str__(self):
        return self.order_id





