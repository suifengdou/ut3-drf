from django.db import models
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.crm.customers.models import Customer
from apps.utils.geography.models import City



class OriOrderInfo(models.Model):

    VERIFY_FIELD = ['buyer_nick', 'trade_no', 'receiver_name', 'receiver_address', 'receiver_mobile',
                    'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                    'src_tids', 'num', 'price', 'share_amount', 'goods_name', 'spec_code', 'order_category',
                    'shop_name', 'logistics_name', 'warehouse_name']

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '未校正订单'),
        (2, '待确认重复订单'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )

    buyer_nick = models.CharField(max_length=150, db_index=True, verbose_name='客户网名', help_text='客户网名')
    trade_no = models.CharField(max_length=60, db_index=True, verbose_name='订单编号', help_text='订单编号')
    receiver_name = models.CharField(max_length=150, verbose_name='收件人', help_text='收件人')
    receiver_address = models.CharField(max_length=256, verbose_name='收货地址', help_text='收货地址')
    receiver_mobile = models.CharField(max_length=40, db_index=True, verbose_name='收件人手机', help_text='收件人手机')
    pay_time = models.DateTimeField(verbose_name='付款时间', help_text='付款时间')
    receiver_area = models.CharField(max_length=150, verbose_name='收货地区', help_text='收货地区')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流单号', help_text='物流单号')
    buyer_message = models.TextField(null=True, blank=True, verbose_name='买家留言', help_text='买家留言')
    cs_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='客服备注', help_text='客服备注')
    src_tids = models.CharField(max_length=101, null=True, blank=True, db_index=True, verbose_name='原始子订单号', help_text='原始子订单号')
    num = models.IntegerField(verbose_name='货品数量', help_text='货品数量')
    price = models.FloatField(verbose_name='成交价', help_text='成交价')
    share_amount = models.FloatField(verbose_name='货品成交总价', help_text='货品成交总价')
    goods_name = models.CharField(max_length=255, verbose_name='货品名称', help_text='货品名称')
    spec_code = models.CharField(max_length=150, verbose_name='商家编码', db_index=True, help_text='商家编码')
    shop_name = models.CharField(max_length=128, verbose_name='店铺', help_text='店铺')
    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='物流公司', help_text='物流公司')
    warehouse_name = models.CharField(max_length=100, verbose_name='仓库', help_text='仓库')
    order_category = models.CharField(max_length=40, db_index=True,  verbose_name='订单类型', help_text='订单类型')
    deliver_time = models.DateTimeField(verbose_name='发货时间', db_index=True, help_text='发货时间')

    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-原始订单'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_ori'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class OrderInfo(models.Model):

    VERIFY_FIELD = ['buyer_nick', 'trade_no', 'receiver_name', 'receiver_address', 'receiver_mobile',
                    'deliver_time', 'pay_time', 'receiver_area', 'logistics_no', 'buyer_message', 'cs_remark',
                    'src_tids', 'num', 'price', 'share_amount', 'goods_name', 'spec_code', 'order_category',
                    'shop_name', 'logistics_name', 'warehouse_name']

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未标记'),
        (3, '未财审'),
        (4, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '已导入过的订单'),
        (2, 'UT中无此店铺'),
        (3, 'UT中店铺关联平台'),
        (4, '保存出错'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '退款'),
    )

    ori_order = models.ForeignKey(OriOrderInfo, on_delete=models.CASCADE, verbose_name='原始订单', help_text='原始订单')
    buyer_nick = models.CharField(max_length=150, db_index=True, verbose_name='客户网名', help_text='客户网名')
    trade_no = models.CharField(max_length=120, db_index=True, verbose_name='订单编号', help_text='订单编号')
    receiver_name = models.CharField(max_length=150, verbose_name='收件人', help_text='收件人')
    receiver_address = models.CharField(max_length=256, verbose_name='收货地址', help_text='收货地址')
    receiver_mobile = models.CharField(max_length=40, db_index=True, verbose_name='收件人手机', help_text='收件人手机')
    pay_time = models.DateTimeField(verbose_name='付款时间', help_text='付款时间')
    receiver_area = models.CharField(max_length=150, verbose_name='收货地区', help_text='收货地区')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流单号', help_text='物流单号')
    buyer_message = models.TextField(null=True, blank=True, verbose_name='买家留言', help_text='买家留言')
    cs_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='客服备注', help_text='客服备注')
    src_tids = models.CharField(max_length=101, null=True, blank=True,  db_index=True,  verbose_name='原始子订单号', help_text='原始子订单号')
    num = models.IntegerField(verbose_name='实发数量', help_text='实发数量')
    price = models.FloatField(verbose_name='成交价', help_text='成交价')
    share_amount = models.FloatField(verbose_name='货品成交总价', help_text='货品成交总价')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品')
    spec_code = models.CharField(max_length=150, verbose_name='商家编码', db_index=True, help_text='商家编码')
    shop_name = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺')
    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='物流公司', help_text='物流公司')
    warehouse_name = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name='仓库')
    order_category = models.CharField(max_length=40, db_index=True,  verbose_name='订单类型', help_text='订单类型')
    deliver_time = models.DateTimeField(verbose_name='发货时间', db_index=True, help_text='发货时间')

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name='客户')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='城市')

    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-UT订单-查询'
        verbose_name_plural = verbose_name
        db_table = 'crm_order'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None

    def cs_info(self):
        cs_info = str(self.receiver_name) + "+" + str(self.receiver_area) + "+" + str(self.receiver_address) + "+" + str(self.receiver_mobile)
        return cs_info
    cs_info.short_description = '客户信息'


class BMSOrderInfo(models.Model):

    VERIFY_FIELD = ["shop_name", "warehouse_name", "pay_time", "order_category", "ori_order_status",
                    "src_tids", "trade_no", "logistics_name", "logistics_no", "buyer_nick", "receiver_name",
                    "province", "city", "district", "street", "receiver_address", "receiver_mobile",
                    "cs_remark", "refund_tag", "order_num", "share_amount", "spec_code", "goods_name",
                    "goods_weight", "dealer_name", "dealer_order_id", "num"]

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '已导入过的订单'),
        (2, '待确认重复订单'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),

    )

    buyer_nick = models.CharField(max_length=150, db_index=True, verbose_name='买家昵称', help_text='买家昵称')
    trade_no = models.CharField(max_length=60, unique=True, db_index=True, verbose_name='仓库订单号', help_text='仓库订单号')
    receiver_name = models.CharField(max_length=150, verbose_name='收货人姓名', help_text='收货人姓名')
    receiver_address = models.CharField(max_length=256, verbose_name='收货人地址', help_text='收货人地址')
    province = models.CharField(max_length=40, verbose_name='省', help_text='省')
    city = models.CharField(max_length=40, verbose_name='市', help_text='市')
    district = models.CharField(max_length=40, verbose_name='区', help_text='区')
    street = models.CharField(max_length=40, verbose_name='街道', help_text='街道')
    receiver_mobile = models.CharField(max_length=40, db_index=True, verbose_name='手机', help_text='手机')
    pay_time = models.DateTimeField(verbose_name='支付时间', help_text='支付时间')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='运单号', help_text='运单号')
    cs_remark = models.TextField(null=True, blank=True, max_length=800, verbose_name='卖家备注', help_text='卖家备注')
    src_tids = models.CharField(max_length=120, db_index=True,  verbose_name='交易订单号', help_text='交易订单号')
    num = models.IntegerField(verbose_name='实发数量', help_text='实发数量')
    price = models.FloatField(verbose_name='货品单价', help_text='货品单价')
    share_amount = models.FloatField(verbose_name='商品小计', help_text='商品小计')
    goods_name = models.CharField(max_length=255, verbose_name='商品名称', help_text='商品名称')
    spec_code = models.CharField(max_length=150, verbose_name='商品编码', db_index=True, help_text='商品编码')
    shop_name = models.CharField(max_length=128, verbose_name='店铺名称', help_text='店铺名称')
    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='快递公司', help_text='快递公司')
    warehouse_name = models.CharField(max_length=100, verbose_name='仓库名称', help_text='仓库名称')
    order_category = models.CharField(max_length=40, db_index=True,  verbose_name='订单类型', help_text='订单类型')
    ori_order_status = models.CharField(max_length=40, verbose_name='状态', help_text='状态')
    goods_weight = models.CharField(max_length=40, verbose_name='商品重量(克)', help_text='商品重量(克)')

    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-原始BMS订单-查询'
        verbose_name_plural = verbose_name
        db_table = 'crm_order_bms'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None



