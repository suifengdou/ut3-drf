from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.department.models import Department
from apps.utils.geography.models import Province, City, District
from apps.base.warehouse.models import Warehouse


class ManualOrder(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已导入'),
        (3, '已完成'),
    )

    ORDER_CATEGORY = (
        (1, '质量问题'),
        (2, '开箱即损'),
        (3, '礼品赠品'),
        (4, '试用体验'),
    )
    SETTLE_CATEGORY = (
        (0, '常规'),
        (1, '试用退回'),
        (2, 'OA报损'),
        (3, '退回苏州'),
        (4, '试用销售'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复递交'),
        (2, '售后配件需要补全sn、部件和描述'),
        (3, '无部门'),
        (4, '省市区出错'),
        (5, '手机错误'),
        (6, '无店铺'),
        (7, '集运仓地址'),
        (8, '14天内重复'),
        (9, '14天外重复'),
        (10, '输出单保存出错'),
        (11, '货品数量错误'),
        (12, '无收件人'),
        (13, '此类型不可发整机'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )
    EXPRESS_LIST = (
        (0, '随机'),
        (1, '顺丰'),
        (2, '圆通'),
        (3, '韵达'),
    )

    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号', help_text='原始单号')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺名称', help_text='店铺名称')
    nickname = models.CharField(max_length=50, verbose_name='网名', help_text='网名')
    receiver = models.CharField(max_length=50, verbose_name='收件人', help_text='收件人')
    address = models.CharField(max_length=250, verbose_name='地址', help_text='地址')
    mobile = models.CharField(max_length=50, db_index=True, verbose_name='手机', help_text='手机')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省', help_text='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市', help_text='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区', help_text='区')

    order_id = models.CharField(null=True, blank=True, max_length=50, verbose_name='订单号', help_text='订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='订单状态', help_text='订单状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人', help_text='处理人')
    order_category = models.SmallIntegerField(choices=ORDER_CATEGORY, default=3, verbose_name='单据类型', help_text='单据类型')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='单据备注', help_text='单据备注')

    m_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='机器序列号', help_text='机器序列号')
    broken_part = models.CharField(null=True, blank=True, max_length=50, verbose_name='故障部位', help_text='故障部位')
    description = models.CharField(null=True, blank=True, max_length=200, verbose_name='故障描述', help_text='故障描述')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name='部门', help_text='部门')
    servicer = models.CharField(null=True, blank=True, max_length=50, verbose_name='客服', help_text='客服')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签', help_text='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    assign_express = models.SmallIntegerField(choices=EXPRESS_LIST, default=0, verbose_name='指定快递', help_text='指定快递')

    track_no = models.CharField(null=True, blank=True, max_length=50, verbose_name='快递单号', help_text='快递单号')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='仓库', help_text='仓库')
    settle_category = models.SmallIntegerField(choices=SETTLE_CATEGORY, default=1, verbose_name='结算类型', help_text='结算类型')
    settle_info = models.CharField(null=True, blank=True, max_length=50, verbose_name='结算信息', help_text='结算信息')
    deliver_time = models.DateTimeField(null=True, blank=True, verbose_name='发货时间', help_text='发货时间')
    amount = models.FloatField(default=0, verbose_name='结算金额', help_text='结算金额')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder'
        permissions = (
            # (权限，权限描述),
            ('view_user_manualorder', 'Can view user DFC-手工订单-用户'),
            ('view_handler_manualorder', 'Can view handler DFC-手工订单-处理'),
        )

    def __str__(self):
        return str(self.id)


class MOGoods(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已导入'),
        (3, '已发货'),
    )

    manual_order = models.ForeignKey(ManualOrder, on_delete=models.CASCADE, verbose_name='原始订单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True)
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.FloatField(default=0, verbose_name='单价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='货品状态')
    logistics_name = models.CharField(null=True, blank=True, max_length=60, verbose_name='物流公司', help_text='物流公司')
    logistics_no = models.CharField(null=True, blank=True, max_length=150, verbose_name='物流单号', help_text='物流单号')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单-货品明细'
        verbose_name_plural = verbose_name
        unique_together = (('manual_order', 'goods_name'))
        db_table = 'dfc_manualorder_goods'
        permissions = (
            # (权限，权限描述),
            ('view_user_mogoods', 'Can view user DFC-手工订单-货品明细-用户'),
            ('view_handler_mogoods', 'Can view handler DFC-手工订单-货品明细-处理'),
        )

    def __str__(self):
        return str(self.id)


class ManualOrderExport(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '驳回'),
        (3, '特殊订单'),
    )
    ori_order = models.OneToOneField(ManualOrder, on_delete=models.CASCADE, verbose_name='手工源单', help_text='手工源单')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺名称', help_text='店铺名称')
    nickname = models.CharField(max_length=50, verbose_name='网名', help_text='网名')
    receiver = models.CharField(max_length=50, verbose_name='收件人', help_text='收件人')
    address = models.CharField(max_length=250, verbose_name='地址', help_text='地址')
    mobile = models.CharField(max_length=50, verbose_name='手机', help_text='手机')

    d_condition = models.CharField(max_length=20, default="款到发货", verbose_name='发货条件', help_text='发货条件')
    discount = models.SmallIntegerField(default=0, verbose_name='优惠金额', help_text='优惠金额')
    post_fee = models.SmallIntegerField(default=0, verbose_name='邮费', help_text='邮费')
    receivable = models.SmallIntegerField(default=0, verbose_name='应收合计', help_text='应收合计')
    goods_price = models.SmallIntegerField(default=0, verbose_name='货品价格', help_text='货品价格')
    total_prices = models.SmallIntegerField(default=0, verbose_name='货品总价', help_text='货品总价')

    goods_id = models.CharField(max_length=50, verbose_name='商家编码', help_text='商家编码')
    goods_name = models.CharField(max_length=50, verbose_name='货品名称', help_text='货品名称')
    quantity = models.SmallIntegerField(verbose_name='货品数量', help_text='货品数量')

    category = models.CharField(max_length=20, default="线下零售", verbose_name='订单类别', help_text='订单类别')
    buyer_remark = models.CharField(max_length=300, verbose_name='买家备注', help_text='买家备注')
    cs_memoranda = models.CharField(max_length=300, verbose_name='客服备注', help_text='客服备注')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省', help_text='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='市', help_text='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区', help_text='区')

    order_id = models.CharField(null=True, blank=True, max_length=50, db_index=True, verbose_name='订单号', help_text='订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='订单状态', help_text='订单状态')
    submit_user = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理人', help_text='处理人')
    erp_order_id = models.CharField(null=True, blank=True, unique=True, max_length=50, verbose_name='原始单号', help_text='原始单号')

    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='店铺名称', help_text='创建者')
    track_no = models.CharField(null=True, blank=True, max_length=50, verbose_name='快递单号', help_text='快递单号')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-手工订单ERP格式导出'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder_export'

    def __str__(self):
        return str(self.id)


class LogManualOrder(models.Model):
    obj = models.ForeignKey(ManualOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'DFC-手工订单-日志'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder_logging'

    def __str__(self):
        return str(self.id)


class LogManualOrderExport(models.Model):
    obj = models.ForeignKey(ManualOrderExport, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'DFC-手工订单ERP格式导出-日志'
        verbose_name_plural = verbose_name
        db_table = 'dfc_manualorder_export_logging'

    def __str__(self):
        return str(self.id)

