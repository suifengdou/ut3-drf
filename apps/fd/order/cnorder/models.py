from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.department.models import Center
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.auth.users.models import UserProfile
from apps.crm.customers.models import Customer


class CNOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待递交'),
        (2, '订单完结'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '快递单号错误'),
        (2, '处理意见为空'),
        (3, '返回的单据无返回单号'),
        (4, '理赔必须设置需理赔才可以审核'),
        (5, '驳回原因为空'),
        (6, '无反馈内容, 不可以审核'),
        (7, '理赔必须设置金额'),
    )

    PROCESSTAG = (
        (0, '未分类'),
        (1, '待截单'),
    )

    shop_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='店铺名称', help_text='店铺名称')
    warehouse_name = models.CharField(max_length=150, db_index=True, verbose_name='仓库名称', help_text='仓库名称')
    is_cod = models.CharField(null=True, blank=True, max_length=150, verbose_name='货到付款', help_text='货到付款')
    order_time = models.DateTimeField(null=True, blank=True, verbose_name='下单时间', help_text='下单时间')
    pay_time = models.DateTimeField(null=True, blank=True, verbose_name='支付时间', help_text='支付时间')
    deliver_time = models.DateTimeField(null=True, blank=True, verbose_name='发货时间', help_text='发货时间')
    sign_time = models.DateTimeField(null=True, blank=True, verbose_name='签收时间', help_text='签收时间')
    order_category = models.CharField(null=True, blank=True, max_length=150, verbose_name='订单类型', help_text='订单类型')
    deliver_type = models.CharField(null=True, blank=True, max_length=150, verbose_name='配送方式', help_text='配送方式')
    ori_order_status = models.CharField(null=True, blank=True, max_length=150, verbose_name='状态', help_text='状态')
    scp_order_id = models.CharField(max_length=150, db_index=True, verbose_name='系统单号', help_text='系统单号')
    order_id = models.CharField(max_length=150, db_index=True, verbose_name='交易订单号', help_text='交易订单号')
    outside_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='外部订单号', help_text='外部订单号')
    odo_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流订单号', help_text='物流订单号')
    warehouse_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='仓库订单号', help_text='仓库订单号')
    logistics = models.CharField(null=True, blank=True, max_length=150, verbose_name='快递公司', help_text='快递公司')
    track_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='运单号', help_text='运单号')
    nickname = models.CharField(null=True, blank=True, max_length=150, verbose_name='买家昵称', help_text='买家昵称')
    receiver = models.CharField(null=True, blank=True, max_length=150, verbose_name='收货人姓名', help_text='收货人姓名')
    province = models.CharField(null=True, blank=True, max_length=150, verbose_name='省', help_text='省')
    city = models.CharField(null=True, blank=True, max_length=150, verbose_name='市', help_text='市')
    district = models.CharField(null=True, blank=True, max_length=150, verbose_name='区', help_text='区')
    town = models.CharField(null=True, blank=True, max_length=150, verbose_name='街道', help_text='街道')
    address = models.CharField(null=True, blank=True, max_length=150, verbose_name='收货人地址', help_text='收货人地址')
    mobile = models.CharField(null=True, blank=True, max_length=150, verbose_name='手机', help_text='手机')
    telephone = models.CharField(null=True, blank=True, max_length=150, verbose_name='电话', help_text='电话')
    order_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='订单金额', help_text='订单金额')
    order_total_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品总售价', help_text='商品总售价')
    express_fee = models.CharField(null=True, blank=True, max_length=150, verbose_name='快递费用', help_text='快递费用')
    cod_fee = models.CharField(null=True, blank=True, max_length=150, verbose_name='COD服务费', help_text='COD服务费')

    paid_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='实收金额', help_text='实收金额')
    remark = models.CharField(null=True, blank=True, max_length=150, verbose_name='卖家备注', help_text='卖家备注')
    is_refund = models.CharField(null=True, blank=True, max_length=150, verbose_name='退款', help_text='退款')
    is_gift = models.CharField(null=True, blank=True, max_length=150, verbose_name='赠品标识', help_text='赠品标识')
    order_quantity = models.CharField(null=True, blank=True, max_length=150, verbose_name='订货数量', help_text='订货数量')
    price = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品售价', help_text='商品售价')
    amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品小计', help_text='商品小计')
    discount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品优惠', help_text='商品优惠')
    goods_code = models.CharField(max_length=150, db_index=True, verbose_name='货品编码', help_text='货品编码')
    goods_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品名称', help_text='商品名称')
    goods_weight = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品重量(克)', help_text='商品重量(克)')
    distributor_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='分销商店铺名称', help_text='分销商店铺名称')
    distributor_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='分销订单号', help_text='分销订单号')
    quantity = models.CharField(null=True, blank=True, max_length=150, verbose_name='实发数量', help_text='实发数量')
    sn = models.CharField(null=True, blank=True, max_length=150, verbose_name='货品唯一码', help_text='货品唯一码')

    is_decrypt = models.BooleanField(default=False, verbose_name='解密标记', help_text='解密标记')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联店铺', help_text='关联店铺')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联仓库',
                                  help_text='关联仓库')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'FD-ORDER-菜鸟-订单'
        verbose_name_plural = verbose_name
        db_table = 'fd_order_cnorder'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["shop_name", "warehouse_name", "is_cod", "order_time", "pay_time", "deliver_time", "sign_time",
                        "order_category", "deliver_type", "ori_order_status", "scp_order_id", "order_id",
                        "outside_order_id", "odo_order_id", "warehouse_order_id", "logistics", "track_no",
                        "nickname", "receiver", "province", "city", "district", "town", "address", "mobile",
                        "telephone", "order_amount", "order_total_amount", "express_fee", "cod_fee", "paid_amount",
                        "remark", "is_refund", "is_gift", "order_quantity", "price", "amount", "discount",
                        "goods_code", "goods_name", "goods_weight", "distributor_name", "distributor_order_id",
                        "quantity", "sn"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class LogCNOrder(models.Model):
    obj = models.ForeignKey(CNOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'FD-ORDER-菜鸟-订单-日志'
        verbose_name_plural = verbose_name
        db_table = 'fd_order_cnorder_logging'

    def __str__(self):
        return str(self.id)


class HistoryCNOrder(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待递交'),
        (2, '订单完结'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '快递单号错误'),
        (2, '处理意见为空'),
        (3, '返回的单据无返回单号'),
        (4, '理赔必须设置需理赔才可以审核'),
        (5, '驳回原因为空'),
        (6, '无反馈内容, 不可以审核'),
        (7, '理赔必须设置金额'),
    )

    PROCESSTAG = (
        (0, '未分类'),
        (1, '待截单'),
    )
    order = models.BigIntegerField(db_index=True, verbose_name="关联单号", help_text="关联单号")
    shop_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='店铺名称', help_text='店铺名称')
    warehouse = models.CharField(max_length=150, db_index=True, verbose_name='仓库名称', help_text='仓库名称')
    is_cod = models.CharField(null=True, blank=True, max_length=150, verbose_name='货到付款', help_text='货到付款')
    order_time = models.DateTimeField(null=True, blank=True, verbose_name='下单时间', help_text='下单时间')
    pay_time = models.DateTimeField(null=True, blank=True, verbose_name='支付时间', help_text='支付时间')
    deliver_time = models.DateTimeField(null=True, blank=True, verbose_name='发货时间', help_text='发货时间')
    sign_time = models.DateTimeField(null=True, blank=True, verbose_name='签收时间', help_text='签收时间')
    order_category = models.CharField(null=True, blank=True, max_length=150, verbose_name='订单类型', help_text='订单类型')
    deliver_type = models.CharField(null=True, blank=True, max_length=150, verbose_name='配送方式', help_text='配送方式')
    ori_order_status = models.CharField(null=True, blank=True, max_length=150, verbose_name='状态', help_text='状态')
    scp_order_id = models.CharField(max_length=150, db_index=True, verbose_name='系统单号', help_text='系统单号')
    order_id = models.CharField(max_length=150, db_index=True, verbose_name='交易订单号', help_text='交易订单号')
    outside_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='外部订单号', help_text='外部订单号')
    odo_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流订单号', help_text='物流订单号')
    warehouse_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='仓库订单号', help_text='仓库订单号')
    logistics = models.CharField(null=True, blank=True, max_length=150, verbose_name='快递公司', help_text='快递公司')
    track_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='运单号', help_text='运单号')
    nickname = models.CharField(null=True, blank=True, max_length=150, verbose_name='买家昵称', help_text='买家昵称')
    receiver = models.CharField(null=True, blank=True, max_length=150, verbose_name='收货人姓名', help_text='收货人姓名')
    province = models.CharField(null=True, blank=True, max_length=150, verbose_name='省', help_text='省')
    city = models.CharField(null=True, blank=True, max_length=150, verbose_name='市', help_text='市')
    district = models.CharField(null=True, blank=True, max_length=150, verbose_name='区', help_text='区')
    town = models.CharField(null=True, blank=True, max_length=150, verbose_name='街道', help_text='街道')
    address = models.CharField(null=True, blank=True, max_length=150, verbose_name='收货人地址', help_text='收货人地址')
    mobile = models.CharField(null=True, blank=True, max_length=150, verbose_name='手机', help_text='手机')
    telephone = models.CharField(null=True, blank=True, max_length=150, verbose_name='电话', help_text='电话')
    order_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='订单金额', help_text='订单金额')
    order_total_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品总售价', help_text='商品总售价')
    express_fee = models.CharField(null=True, blank=True, max_length=150, verbose_name='快递费用', help_text='快递费用')
    cod_fee = models.CharField(null=True, blank=True, max_length=150, verbose_name='COD服务费', help_text='COD服务费')

    paid_amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='实收金额', help_text='实收金额')
    remark = models.CharField(null=True, blank=True, max_length=150, verbose_name='卖家备注', help_text='卖家备注')
    is_refund = models.CharField(null=True, blank=True, max_length=150, verbose_name='退款', help_text='退款')
    is_gift = models.CharField(null=True, blank=True, max_length=150, verbose_name='赠品标识', help_text='赠品标识')
    order_quantity = models.CharField(null=True, blank=True, max_length=150, verbose_name='订货数量', help_text='订货数量')
    price = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品售价', help_text='商品售价')
    amount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品小计', help_text='商品小计')
    discount = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品优惠', help_text='商品优惠')
    goods_code = models.CharField(max_length=150, db_index=True, verbose_name='货品编码', help_text='货品编码')
    goods_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品名称', help_text='商品名称')
    goods_weight = models.CharField(null=True, blank=True, max_length=150, verbose_name='商品重量(克)', help_text='商品重量(克)')
    distributor_name = models.CharField(null=True, blank=True, max_length=150, verbose_name='分销商店铺名称', help_text='分销商店铺名称')
    distributor_order_id = models.CharField(null=True, blank=True, max_length=150, verbose_name='分销订单号', help_text='分销订单号')
    quantity = models.CharField(null=True, blank=True, max_length=150, verbose_name='实发数量', help_text='实发数量')
    sn = models.CharField(null=True, blank=True, max_length=150, verbose_name='货品唯一码', help_text='货品唯一码')

    is_decrypt = models.BooleanField(default=False, verbose_name='解密标记', help_text='解密标记')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联店铺', help_text='关联店铺')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联仓库', help_text='关联仓库')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'FD-ORDER-菜鸟-历史订单'
        verbose_name_plural = verbose_name
        db_table = 'fd_order_cnorder_history'

    def __str__(self):
        return str(self.id)


class LogHistoryCNOrder(models.Model):
    obj = models.ForeignKey(CNOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'FD-ORDER-菜鸟-历史订单-日志'
        verbose_name_plural = verbose_name
        db_table = 'fd_order_cnorder_history_logging'

    def __str__(self):
        return str(self.id)





