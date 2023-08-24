from django.db import models
from apps.psi.inbound.models import InboundDetail
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from apps.base.warehouse.models import Warehouse


# 翻新单
class Renovation(models.Model):
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待处理'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
        (5, '已驳回'),
        (9, '特殊'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '无SN'),
        (2, '已关联出库单，联系管理员'),
        (3, '创建出库单出错'),
        (4, '创建出库单明细出错'),
        (5, '存在配件出库明细不可以取消'),
        (6, '非特殊无配件不可审核'),
        (7, '关联出库单错误，联系管理员'),
        (8, '关联出库单创建错误'),
        (9, '未锁定单据不可审核'),
        (10, '未锁定单据不可设置特殊标记'),
        (11, '已出库单据不可重复出库'),
        (12, '库存不存在'),
        (13, '缺货无法出库'),
        (14, '出库单据未出库配件'),
        (15, '出库单据未出库残品'),
        (16, '出库单据已存在正品入库单'),
        (17, '已操作出库单据无法驳回'),
        (18, '出库数量错误'),
    )
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待翻新'),
        (2, '待入库'),
        (3, '已完结'),
    )
    order = models.ForeignKey(InboundDetail, on_delete=models.CASCADE, null=True, blank=True, verbose_name='关联单')
    code = models.CharField(max_length=90, db_index=True, verbose_name='翻新单号', help_text='翻新单号')
    sn = models.CharField(null=True, blank=True, max_length=60, verbose_name='SN码', help_text='SN码')
    verification = models.CharField(max_length=150, null=True, blank=True, verbose_name='验证号')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, null=True, blank=True, verbose_name='货品名称')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='仓库', help_text='仓库')

    is_using = models.BooleanField(default=False, verbose_name='配件出库', help_text='配件出库')
    is_parts = models.BooleanField(default=False, verbose_name='详情设置', help_text='详情设置')

    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='到货状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-翻新单'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation'

    def __str__(self):
        return str(self.id)


# 翻新单配件品明细
class RenovationGoods(models.Model):
    PROCESSTAG = (
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
    order = models.ForeignKey(Renovation, on_delete=models.CASCADE, verbose_name='翻新单')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='配件名称')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.FloatField(default=0, verbose_name='价格')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='到货状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-翻新单-配件明细'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_goods'

    def __str__(self):
        return str(self.id)


# 翻新单使用详情
class Renovationdetail(models.Model):
    PROCESSTAG = (
        (0, '未处理'),
        (1, '待处理'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
    )
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待递交'),
        (2, '待入库'),
        (3, '部分到货'),
        (4, '已到货'),
    )
    order = models.ForeignKey(Renovation, on_delete=models.CASCADE, verbose_name='货品名称')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称')
    is_used = models.BooleanField(default=False, verbose_name='是否使用', help_text='是否使用')
    is_loss = models.BooleanField(default=False, verbose_name='是否丢失', help_text='是否丢失')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='明细状态')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-翻新单-使用详情'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_detail'

    def __str__(self):
        return str(self.id)


class LogRenovation(models.Model):
    obj = models.ForeignKey(Renovation, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-翻新单-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_logging'

    def __str__(self):
        return str(self.id)


class LogRenovationGoods(models.Model):
    obj = models.ForeignKey(RenovationGoods, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-翻新单-配件明细-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_goods_logging'

    def __str__(self):
        return str(self.id)


class LogRenovationdetail(models.Model):
    obj = models.ForeignKey(Renovationdetail, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'PSI-翻新单-使用详情-日志'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_detail_logging'

    def __str__(self):
        return str(self.id)


class ROFiles(models.Model):
    name = models.CharField(max_length=150, verbose_name='文件名称', help_text='文件名称')
    suffix = models.CharField(max_length=100, verbose_name='文件类型', help_text='文件类型')
    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(Renovation, on_delete=models.CASCADE, verbose_name='手工单', help_text='手工单')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'PSI-翻新单-文档'
        verbose_name_plural = verbose_name
        db_table = 'psi_renovation_files'

    def __str__(self):
        return str(self.id)


