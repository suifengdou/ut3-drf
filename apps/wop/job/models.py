from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.department.models import Center
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from apps.crm.customers.models import Customer
from apps.crm.labels.models import Label
from apps.dfc.manualorder.models import ManualOrder
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.base.department.models import Department, Center
from apps.utils.geography.models import Province, City, District


class JobCategory(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型名称', help_text='类型名称')
    code = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型编码', help_text='类型编码')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-JOB-任务-类型'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_category'

    def __str__(self):
        return str(self.id)


class JobOrder(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未递交'),
        (3, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '存在未递交的明细'),
        (2, '存在明细错误'),
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
        (9, '驳回'),
        (5, '特殊订单'),
    )
    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='任务名称', help_text='任务名称')
    code = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='任务编码', help_text='任务编码')
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, null=True, blank=True, verbose_name='任务类型', help_text='任务类型')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='任务部门', help_text='任务部门')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, verbose_name='任务中心', help_text='任务中心')
    info = models.TextField(null=True, blank=True, verbose_name='任务说明', help_text='任务说明')
    quantity = models.IntegerField(default=0, verbose_name="数量", help_text="数量")
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order'

    def __str__(self):
        return str(self.id)


class JOFiles(models.Model):

    name = models.CharField(max_length=150, verbose_name='文件名称', help_text='文件名称')
    suffix = models.CharField(max_length=100, verbose_name='文件类型', help_text='文件类型')
    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(JobOrder, on_delete=models.CASCADE, verbose_name='子项项目', help_text='子项项目')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='创建人', help_text='创建人')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-文档'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_files'

    def __str__(self):
        return str(self.id)


class JobOrderDetails(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未递交'),
        (3, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '明细对应标签单状态错误'),
        (2, '明细对应客户已存在标签'),
        (3, '创建标签出错'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (9, '驳回'),
        (5, '特殊订单'),
    )
    order = models.ForeignKey(JobOrder, on_delete=models.CASCADE, verbose_name='源单', help_text='源单')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-明细'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_details'

    def __str__(self):
        return str(self.id)

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['customer', 'code', 'memo']

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class JODFiles(models.Model):

    name = models.CharField(max_length=150, verbose_name='文件名称', help_text='文件名称')
    suffix = models.CharField(max_length=100, verbose_name='文件类型', help_text='文件类型')
    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(JobOrderDetails, on_delete=models.CASCADE, verbose_name='工单明细', help_text='工单明细')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='创建人', help_text='创建人')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-明细-文档'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_details_files'

    def __str__(self):
        return str(self.id)


class LogJobCategory(models.Model):
    obj = models.ForeignKey(JobCategory, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'WOP-JOB-任务-类型-日志'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_category_logging'

    def __str__(self):
        return str(self.id)


class LogJobOrder(models.Model):
    obj = models.ForeignKey(JobOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-日志'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_logging'

    def __str__(self):
        return str(self.id)


class LogJobOrderDetails(models.Model):
    obj = models.ForeignKey(JobOrderDetails, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-明细-日志'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_details_logging'

    def __str__(self):
        return str(self.id)


class InvoiceJobOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待递交'),
        (2, '等待审核'),
        (3, '递交成功'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '电话错误'),
        (2, '无收件人'),
        (3, '地址无法提取省市区'),
        (4, '无UT单号'),
        (5, '已存在已发货订单'),
        (6, '创建手工单出错'),
        (7, '创建手工单货品出错'),
        (8, '无货品不可审核'),
        (9, '不可重复递交'),
    )

    PROCESSTAG = (
        (0, '无'),
        (1, '近30天内重复'),
        (2, '近30天外重复'),
    )

    job_order = models.ForeignKey(JobOrder, on_delete=models.CASCADE, verbose_name='服务单', help_text='服务单')
    manual_order = models.OneToOneField(ManualOrder, on_delete=models.CASCADE, verbose_name='服务单', help_text='服务单')
    order_id = models.CharField(null=True, blank=True, max_length=120, verbose_name='来源单号', help_text='来源单号')
    erp_order_id = models.CharField(unique=True, null=True, blank=True, max_length=100, verbose_name='发货编号', help_text='发货编号')
    title = models.CharField(max_length=120, verbose_name='工单标题', help_text='工单标题')
    nickname = models.CharField(max_length=120, verbose_name='用户ID', help_text='用户ID')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='用户', help_text='用户')

    receiver = models.CharField(max_length=150, verbose_name='客户姓名', help_text='客户姓名')
    address = models.CharField(max_length=150, verbose_name='客户地址', help_text='客户地址')
    mobile = models.CharField(max_length=60, db_index=True, verbose_name='手机', help_text='手机')
    cost = models.FloatField(default=0, verbose_name='服务金额', help_text='服务金额')
    quantity = models.IntegerField(default=0, verbose_name='货品总数', help_text='货品总数')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name='部门')
    demand = models.CharField(max_length=150, verbose_name='诉求', help_text='诉求')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')
    rejection = models.CharField(null=True, blank=True, max_length=250, verbose_name='驳回原因', help_text='驳回原因')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-发货单'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_invoice'

        # permissions = (
        #     # (权限，权限描述),
        #     ('view_user_invoiceworkorder', 'Can view user WOP-用户体验工单-服务单-发货单-用户'),
        #     ('view_handler_invoiceworkorder', 'Can view handler WOP-用户体验工单-服务单-发货单-处理'),
        #     ('view_check_invoiceworkorder', 'Can view check WOP-用户体验工单-服务单-发货单-审核'),
        # )

    def __str__(self):
        return str(self.id)


class IJOGoods(models.Model):
    CATEGORY = (
        (1, '发出货品'),
        (2, '退回货品'),
        (3, '单纯费用'),
        (4, '单纯收入'),
    )
    invoice = models.ForeignKey(InvoiceJobOrder, on_delete=models.CASCADE, verbose_name='发货单', help_text='发货单')
    category = models.SmallIntegerField(choices=CATEGORY, default=1, verbose_name='发货类型', help_text='发货类型')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True, help_text='货品编码')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称', help_text='货品名称')
    quantity = models.IntegerField(verbose_name='数量', help_text='数量')
    price = models.FloatField(verbose_name='单价', help_text='单价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')


    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-发货单-货品'
        verbose_name_plural = verbose_name
        unique_together = (('invoice', 'goods_name'))
        db_table = 'wop_job_order_invoice_goods'

    def __str__(self):
        return str(self.id)


class LogInvoiceJobOrder(models.Model):
    obj = models.ForeignKey(InvoiceJobOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-发货单'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_invoice_logging'

    def __str__(self):
        return str(self.id)


class LogIJOGoods(models.Model):
    obj = models.ForeignKey(JobOrderDetails, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'WOP-JOB-任务-工单-发货单-货品-日志'
        verbose_name_plural = verbose_name
        db_table = 'wop_job_order_invoice_goods_logging'

    def __str__(self):
        return str(self.id)
