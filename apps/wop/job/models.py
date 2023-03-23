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
from apps.crm.labels.models import Label


class JobCategory(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型名称', help_text='类型名称')
    code = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型编码', help_text='类型编码')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
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
        (1, '待递交'),
        (2, '待执行'),
        (3, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '任务明细未完整确认'),
        (2, '存在未锁定单据明细'),
        (3, '任务明细非初始状态'),
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
    name = models.CharField(max_length=200, db_index=True, null=True, blank=True, verbose_name='任务名称', help_text='任务名称')
    code = models.CharField(max_length=120, unique=True, db_index=True, null=True, blank=True, verbose_name='任务编码', help_text='任务编码')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, null=True, blank=True, verbose_name='标签', help_text='标签')
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, null=True, blank=True, verbose_name='任务类型', help_text='任务类型')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='任务部门', help_text='任务部门')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, verbose_name='任务中心', help_text='任务中心')
    info = models.TextField(null=True, blank=True, verbose_name='任务说明', help_text='任务说明')
    quantity = models.IntegerField(default=0, verbose_name="数量", help_text="数量")
    keywords = models.CharField(max_length=200, null=True, blank=True, verbose_name='任务关键字', help_text='任务关键字')
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
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
        (1, '待处理'),
        (2, '待领取'),
        (3, '待执行'),
        (4, '待审核'),
        (5, '已完成'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '单据已锁定无法锁定'),
        (2, '先锁定再审核'),
        (3, '先设置完成按钮或结束按钮'),
        (4, '无操作内容'),
        (5, '标签创建错误'),
        (6, '标签删除错误'),
        (7, '工单默认标签创建错误'),

    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (9, '驳回'),
        (5, '特殊订单'),
    )
    order = models.ForeignKey(JobOrder, on_delete=models.CASCADE, verbose_name='源单', help_text='源单')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    add_label = models.CharField(max_length=200, null=True, blank=True, verbose_name='添加标签', help_text='添加标签')
    del_label = models.CharField(max_length=200, null=True, blank=True, verbose_name='删除标签', help_text='删除标签')
    is_complete = models.BooleanField(default=False, verbose_name='是否完成', help_text='是否完成')
    is_over = models.BooleanField(default=False, verbose_name='是否结束', help_text='是否结束')
    is_reset = models.BooleanField(default=False, verbose_name='是否重置', help_text='是否重置')
    delay = models.IntegerField(default=0, verbose_name='延迟天数', help_text='延迟天数')
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    content = models.CharField(max_length=240, null=True, blank=True, verbose_name='操作内容', help_text='操作内容')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='领取人', help_text='领取人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='领取时间', help_text='领取时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='领取间隔(分钟)', help_text='领取间隔(分钟)')

    completer = models.CharField(null=True, blank=True, max_length=30, verbose_name='完成人', help_text='完成人')
    completed_time = models.DateTimeField(null=True, blank=True, verbose_name='完成时间', help_text='完成时间')
    completed_interval = models.IntegerField(null=True, blank=True, verbose_name='完成间隔(分钟)', help_text='完成间隔(分钟)')

    checker = models.CharField(null=True, blank=True, max_length=30, verbose_name='审核人', help_text='审核人')
    checked_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间', help_text='审核时间')

    confirmer = models.CharField(null=True, blank=True, max_length=30, verbose_name='确认人', help_text='确认人')
    confirmed_time = models.DateTimeField(null=True, blank=True, verbose_name='确认时间', help_text='确认时间')
    confirmed_interval = models.IntegerField(null=True, blank=True, verbose_name='确认间隔(分钟)', help_text='确认间隔(分钟)')

    appeal = models.CharField(null=True, blank=True, max_length=250, verbose_name='申诉理由', help_text='申诉理由')
    judgment = models.CharField(null=True, blank=True, max_length=250, verbose_name='终审内容', help_text='终审内容')
    cost = models.FloatField(default=0, verbose_name='服务金额', help_text='服务金额')

    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(null=True, blank=True, max_length=260, verbose_name='驳回原因', help_text='驳回原因')

    job_index = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)],
                                    verbose_name='任务指数', help_text='任务指数')
    int_index_1 = models.IntegerField(default=0, verbose_name='整型指标1', help_text='整型指标1')
    int_index_2 = models.IntegerField(default=0, verbose_name='整型指标2', help_text='整型指标2')
    int_index_3 = models.IntegerField(default=0, verbose_name='整型指标3', help_text='整型指标3')
    float_index_1 = models.FloatField(default=0, verbose_name='浮点指标1', help_text='浮点指标1')
    float_index_2 = models.FloatField(default=0, verbose_name='浮点指标1', help_text='浮点指标1')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误标签')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    memo = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
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


