# coding=utf-8
from django.db import models
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.utils.geography.models import Province, City, District
# Create your models here.


class OriginData(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '地址无法提取省市区'),
        (2, '手机号错误'),
        (3, '集运仓地址'),
        (4, '重复递交'),
        (5, '输出单保存出错'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺名称')
    order_id = models.CharField(max_length=50, db_index=True, verbose_name='订单号')
    nickname = models.CharField(max_length=50, verbose_name='网名')
    receiver = models.CharField(max_length=50, verbose_name='收件人')
    address = models.CharField(max_length=250, verbose_name='地址')
    mobile = models.CharField(max_length=50, verbose_name='手机')

    goods_id = models.CharField(max_length=50, verbose_name='商家编码')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.SmallIntegerField(verbose_name='货品数量')

    buyer_remark = models.CharField(max_length=300, null=True, blank=True, verbose_name='买家备注')
    cs_memoranda = models.CharField(max_length=300, null=True, blank=True, verbose_name='客服备注')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人')
    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-原始批量赠品单'
        verbose_name_plural = verbose_name
        unique_together = (("order_id", "goods_name"),)
        db_table = 'dfc_origindata'

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["shop", "order_id", "nickname", "receiver", "address", "mobile", "goods_name", "quantity", "buyer_remark"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class BatchTable(models.Model):
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
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.SmallIntegerField(verbose_name='货品数量')

    category = models.CharField(max_length=20, default="线下零售", verbose_name='订单类别')
    buyer_remark = models.CharField(max_length=300, verbose_name='买家备注')
    cs_memoranda = models.CharField(max_length=300, verbose_name='客服备注')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    order_id = models.CharField(null=True, blank=True, max_length=50, db_index=True, verbose_name='订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人')
    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-批量赠品单'
        verbose_name_plural = verbose_name
        unique_together = (("shop", "order_id", "goods_id"),)
        db_table = 'dfc_batchtable'

    def __str__(self):
        return self.order_id