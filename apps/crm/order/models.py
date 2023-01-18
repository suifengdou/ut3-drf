# coding: utf8
from django.db import models
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.crm.customers.models import Customer
from apps.utils.geography.models import City
from apps.auth.users.models import UserProfile


class OriOrder(models.Model):


    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未递交'),
        (3, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '非待解密订单无需解密'),
        (2, '待确认重复订单'),
        (3, 'UT未创建货品'),
        (4, 'UT未创建店铺'),
        (5, 'UT未创建仓库'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已解密'),
        (2, '已建档'),
        (3, '没法解'),
        (4, '有退款'),
        (5, '特殊'),
        (9, '驳回'),
    )
    CATEGORY_LIST = (
        (1, '出库明细'),
        (2, '订单明细'),
    )
    buyer_nick = models.CharField(max_length=150, db_index=True, null=True, blank=True, verbose_name='客户网名', help_text='客户网名')
    trade_no = models.CharField(max_length=60, db_index=True, verbose_name='订单编号', help_text='订单编号')
    src_tids = models.CharField(max_length=101, null=True, blank=True, db_index=True, verbose_name='子单原始单号',
                                help_text='子单原始单号')
    sub_src_tids = models.CharField(max_length=101, null=True, blank=True, db_index=True, verbose_name='子单原始子订单号',
                                help_text='子单原始子订单号')
    receiver = models.CharField(max_length=150, null=True, blank=True, verbose_name='收件人', help_text='收件人')
    address = models.CharField(max_length=256, null=True, blank=True, verbose_name='收货地址', help_text='收货地址')
    mobile = models.CharField(max_length=40, db_index=True, null=True, blank=True, verbose_name='收件人手机', help_text='收件人手机')
    pay_time = models.DateTimeField(verbose_name='付款时间', help_text='付款时间')
    area = models.CharField(max_length=150, verbose_name='收货地区', help_text='收货地区')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流单号', help_text='物流单号')
    buyer_message = models.TextField(null=True, blank=True, verbose_name='买家留言', help_text='买家留言')
    cs_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='客服备注', help_text='客服备注')
    print_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='打印备注', help_text='打印备注')

    num = models.IntegerField(default=0, verbose_name='下单数量', help_text='下单数量')
    quantity = models.IntegerField(default=0, verbose_name='实发数量', help_text='实发数量')
    price = models.FloatField(default=0, verbose_name='成交价', help_text='成交价')
    weight = models.FloatField(default=0, verbose_name='预估重量', help_text='预估重量')
    actual_weight = models.FloatField(default=0, verbose_name='实际重量', help_text='实际重量')
    amount = models.FloatField(verbose_name='成交总价', help_text='成交总价')
    goods_name = models.CharField(max_length=255, verbose_name='货品名称', help_text='货品名称')
    spec_code = models.CharField(max_length=150, verbose_name='商家编码', db_index=True, help_text='商家编码')
    shop_name = models.CharField(max_length=128, verbose_name='店铺', help_text='店铺')
    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='物流公司', help_text='物流公司')
    warehouse_name = models.CharField(max_length=100, verbose_name='仓库名称', help_text='仓库名称')
    order_category = models.CharField(max_length=40, db_index=True,  verbose_name='订单类型', help_text='订单类型')
    erp_order_status = models.CharField(max_length=40, db_index=True,  verbose_name='erp订单状态', help_text='erp订单状态')
    deliver_time = models.DateTimeField(null=True, blank=True, verbose_name='发货时间', db_index=True, help_text='发货时间')
    sign = models.CharField(max_length=40, db_index=True, default='无', verbose_name='erp订单标记', help_text='erp订单标记')

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name='客户',
                                 help_text='客户')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, null=True, blank=True, verbose_name='货品', help_text='货品')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺', help_text='店铺')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='仓库', help_text='仓库')
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0,  db_index=True, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')
    category = models.SmallIntegerField(choices=CATEGORY_LIST, default=1,  db_index=True, verbose_name='来源类型', help_text='来源类型')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-订单-原始订单'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_ori'
        permissions = (
            # (权限，权限描述),
            ('view_user_orderinfo', 'Can view user CRM-UT订单-用户'),
            ('view_handler_orderinfo', 'Can view handler CRM-UT订单-处理'),
        )

    def __str__(self):
        return str(self.id)

    @property
    def cs_info(self):
        cs_info = str(self.name) + "+" + str(self.area) + "+" + str(self.address) + "+" + str(self.smartphone)
        return cs_info


class DecryptOrder(models.Model):

    VERIFY_FIELD = ['buyer_nick', 'trade_no', 'receiver', 'address', 'mobile', 'sub_src_tids',
                    'src_tids', 'area', 'buyer_message', 'cs_remark']

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未解密'),
        (2, '已解密'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '未校正订单'),
        (2, '待确认重复订单'),
        (3, 'UT未创建货品'),
        (4, 'UT未创建店铺'),
        (5, 'UT未创建仓库'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )

    buyer_nick = models.CharField(max_length=150, db_index=True, verbose_name='客户网名', help_text='客户网名')
    trade_no = models.CharField(max_length=60, db_index=True, verbose_name='订单编号', help_text='订单编号')
    receiver = models.CharField(max_length=150, verbose_name='收件人', help_text='收件人')
    address = models.CharField(max_length=256, verbose_name='收货地址', help_text='收货地址')
    mobile = models.CharField(max_length=40, db_index=True, verbose_name='收件人手机', help_text='收件人手机')

    area = models.CharField(max_length=150, verbose_name='收货地区', help_text='收货地区')
    buyer_message = models.TextField(null=True, blank=True, verbose_name='买家留言', help_text='买家留言')
    cs_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='客服备注', help_text='客服备注')
    src_tids = models.CharField(max_length=101, null=True, blank=True, db_index=True, verbose_name='原始子订单号', help_text='原始子订单号')

    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-订单-解密库'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_ori_decrypt'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class LogOriOrder(models.Model):
    obj = models.ForeignKey(OriOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-订单-原始订单-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_ori_logging'

    def __str__(self):
        return str(self.id)


class LogDecryptOrder(models.Model):
    obj = models.ForeignKey(DecryptOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-订单-解密库-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_ori_decrypt_logging'

    def __str__(self):
        return str(self.id)


