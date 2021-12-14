from django.db import models
from apps.base.company.models import Company
from apps.utils.geography.models import Nationality
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.int.intdistributor.models import IntDistributor
from apps.int.intaccount.models import Currency, IntAccount
from apps.base.goods.models import Goods
from apps.base.department.models import Department


# Create your models here.
class IntPurchaseOrder(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待审核'),
        (2, '待处理'),
        (3, '待结算'),
        (4, '已完成'),
    )
    CATEGORY_LIST = (
        (1, '样机'),
        (2, '订单'),
    )
    COLLECTION_STATUS = (
        (0, '未收款'),
        (1, '已收定'),
        (2, '已收款'),
    )

    MODE_LIST = (
        (1, 'FOB'),
        (2, 'CIF'),
        (3, 'EXW'),
        (4, 'DDP'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '货品金额为零'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )
    SIGN_LIST = (
        (0, '无'),
        (1, '未付定金未排产'),
        (2, '未付定金已排产'),
        (3, '未付定金未发货'),
        (4, '未付定金已发货'),
        (5, '已付定金未排产'),
        (6, '已付定金已排产'),
        (7, '已付定金未发货'),
        (8, '已付定金已发货'),
        (9, '未付尾款未发货'),
        (10, '未付尾款已发货'),
        (11, '已付尾款未发货'),
        (12, '已付尾款已发货'),
    )

    order_id = models.CharField(unique=True, max_length=200, db_index=True, verbose_name='PI单号', help_text='PI单号')
    distributor = models.ForeignKey(IntDistributor, on_delete=models.CASCADE, verbose_name='经销商', help_text='经销商')
    order_category = models.SmallIntegerField(choices=CATEGORY_LIST, default=1, verbose_name='类型', help_text='类型')
    contract_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='合同编号', help_text='合同编号')

    account = models.ForeignKey(IntAccount, on_delete=models.CASCADE, verbose_name='收款账户', help_text='收款账户')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, blank=True, verbose_name='币种', help_text='币种')

    trade_mode = models.SmallIntegerField(choices=MODE_LIST, default=1, verbose_name='贸易方式', help_text='贸易方式')

    amount = models.FloatField(default=0, verbose_name='采购单总金额', help_text='采购单总金额')
    actual_amount = models.FloatField(default=0, verbose_name='实收总金额', help_text='实收总金额')
    virtual_amount = models.FloatField(default=0, verbose_name='销减总金额', help_text='销减总金额')
    deposit = models.FloatField(default=0, verbose_name='定金', help_text='定金')

    quantity = models.IntegerField(default=0, verbose_name="货品总数", help_text="货品总数")
    address = models.CharField(null=True, blank=True, max_length=250, verbose_name='地址', help_text='地址')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    sign = models.SmallIntegerField(choices=SIGN_LIST, default=0, verbose_name='标记', help_text='标记')

    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name='部门')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', help_text='单据状态')
    collection_status = models.IntegerField(choices=COLLECTION_STATUS, default=0, verbose_name='收款状态', help_text='收款状态')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签', help_text='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际采购单'
        verbose_name_plural = verbose_name
        db_table = 'int_purchase_order'
        permissions = (
            ('view_user_intpurchaseorder',  'Can view user INT-国际采购单'),
            ('view_handler_intpurchaseorder', 'Can view handler INT-国际采购单'),
        )

    def __str__(self):
        return str(self.order_id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["shop", "order_id", "nickname", "receiver", "address", "mobile", "goods_name", "quantity", "buyer_remark"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class IPOGoods(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未发货'),
        (2, '部分发货'),
        (3, '已发货'),
    )

    ipo = models.ForeignKey(IntPurchaseOrder, on_delete=models.CASCADE, verbose_name='采购单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True)
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.IntegerField(verbose_name='数量')
    actual_quantity = models.IntegerField(default=0, verbose_name='实发数量')
    price = models.FloatField(verbose_name='单价')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name='币种', help_text='币种')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='货品状态')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际采购单-货品明细'
        verbose_name_plural = verbose_name
        unique_together = (('ipo', 'goods_name'))
        db_table = 'int_purchase_order_goods'
        permissions = (
            ('view_user_ipogoods',  'Can view user INT-国际采购单-货品明细'),
            ('view_handler_ipogoods', 'Can view handler INT-国际采购单-货品明细'),
        )

    def __str__(self):
        return str(self.goods_id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["shop", "order_id", "nickname", "receiver", "address", "mobile", "goods_name", "quantity", "buyer_remark"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None



