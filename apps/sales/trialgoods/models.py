from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.department.models import Department
from apps.utils.geography.models import Province, City, District
from apps.base.warehouse.models import Warehouse
from apps.dfc.manualorder.models import ManualOrder, LogManualOrder, MOGoods


# 尾货售后单
class RefundManualOrder(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待递交'),
        (2, '待处理'),
        (3, '待结算'),
        (4, '已完成'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待核实'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
        (5, '部分到货'),
        (6, '已到货'),
        (7, '换货'),
        (8, '驳回'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '退换数量超出原单数量'),
        (2, '退换金额超出原单金额'),
        (3, '无退货原因'),
        (4, '无返回快递单号'),
        (5, '已存在关联入库，不可以驳回'),
        (6, '非换货单不可以标记'),
        (7, '非已到货状态不可以审核'),
        (8, '退换数量和收货数量不一致'),
        (9, '退换金额和收货金额不一致'),
        (10, '关联预存单出错'),
        (11, '当前登录人无预存账户'),
        (12, '创建预存单错误'),
        (13, '关联的订单未发货'),
        (14, '不是退货单不可以审核'),
        (15, '物流单号重复'),
        (16, '入库单已经操作，不可以清除标记'),
        (17, '重复生成结算单，联系管理员'),
        (18, '生成结算单出错'),
        (19, '保存流水出错'),
        (20, '保存流水验证出错'),
    )
    MODE_W = (
        (0, '回流'),
        (1, '二手'),
    )

    CATEGORY = (
        (3, '退-退货退款'),
        (4, '退-换货退回'),
        (5, '退-仅退款'),
    )

    tail_order = models.OneToOneField(MOGoods, on_delete=models.CASCADE, related_name='refund_tail_order', verbose_name='来源单号')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺')
    order_id = models.CharField(unique=True, max_length=100, null=True, blank=True, verbose_name='退换单号', db_index=True)
    order_category = models.SmallIntegerField(choices=CATEGORY, default=3, verbose_name='退款类型')
    mode_warehouse = models.SmallIntegerField(choices=MODE_W, null=True, blank=True, verbose_name='发货模式')
    sent_consignee = models.CharField(null=True, blank=True, max_length=150, verbose_name='收件人姓名')
    sent_smartphone = models.CharField(null=True, blank=True, max_length=30, verbose_name='收件人手机')
    sent_city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='收件城市')
    sent_district = models.CharField(null=True, blank=True, max_length=30, verbose_name='收件区县')
    sent_address = models.CharField(null=True, blank=True, max_length=200, verbose_name='收件地址')

    quantity = models.IntegerField(null=True, blank=True, verbose_name='货品总数')

    amount = models.FloatField(default=0, verbose_name='申请退款总额')
    ori_amount = models.FloatField(null=True, blank=True, verbose_name='源订单总额')

    receipted_quantity = models.IntegerField(default=0, verbose_name='到货总数')
    receipted_amount = models.FloatField(default=0, verbose_name='到货退款总额')

    track_no = models.CharField(max_length=150, null=True, blank=True, verbose_name='返回快递信息')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='申请提交时间')

    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='退款处理时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='退款处理间隔(分钟)')

    message = models.TextField(null=True, blank=True, verbose_name='工单留言')
    feedback = models.TextField(null=True, blank=True, verbose_name='工单反馈')

    info_refund = models.TextField(null=True, blank=True, verbose_name='退换货信息原因')

    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='订单状态')
    fast_tag = models.BooleanField(default=True, verbose_name='快捷状态')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-尾货退货单'
        verbose_name_plural = verbose_name
        db_table = 'sales_tailgoods_refund'
        permissions = (
            ('view_user_refundorder',  'Can view user SALES-尾货退货单'),
            ('view_handler_refundorder', 'Can view handler SALES-尾货退货单'),
            ('view_check_refundorder', 'Can view check SALES-尾货退货单'),
        )

    def __str__(self):
        return str(self.order_id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['order_id', 'information', 'category']
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None

    def goods_name(self):
        goods_name = self.rogoods_set.all()
        if len(goods_name) == 1:
            goods_name = goods_name[0].goods_name.goods_name
        elif len(goods_name) > 1:
            goods_name = '多种'
        else:
            goods_name = '无'
        return goods_name

    goods_name.short_description = '单据货品'


# 尾货退款订单货品明细
class RMOGoods(models.Model):
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待处理'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '入库数量是0'),
        (2, '入库数和待收货数不符'),
        (3, '入库单未确认'),
        (4, '退款单未完整入库'),
    )
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待递交'),
        (2, '待入库'),
        (3, '部分到货'),
        (4, '已到货'),
    )
    refund_order = models.ForeignKey(RefundManualOrder, on_delete=models.CASCADE, verbose_name='退款订单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True)
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.IntegerField(verbose_name='退换货数量')
    receipted_quantity = models.IntegerField(default=0, verbose_name='到货数量')
    settlement_price = models.FloatField(verbose_name='结算单价')
    settlement_amount = models.FloatField(verbose_name='货品结算总价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='到货状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-尾货退货单-货品明细'
        verbose_name_plural = verbose_name
        db_table = 'sales_tailgoods_refund_goods'
        permissions = (
            ('view_user_rogoods',  'Can view user SALES-尾货退货单-货品明细'),
            ('view_handler_rogoods', 'Can view handler SALES-尾货退货单-货品明细'),
        )

    def __str__(self):
        return self.refund_order.order_id