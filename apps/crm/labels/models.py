from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.department.models import Center
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile
from apps.crm.customers.models import Customer


class LabelCategory(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型名称', help_text='类型名称')
    code = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='类型编码', help_text='类型编码')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-LABEL-标签类型'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_category'

    def __str__(self):
        return str(self.id)


class Label(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='标签名称', help_text='标签名称')
    code = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='标签编码', help_text='标签编码')
    category = models.ForeignKey(LabelCategory, on_delete=models.CASCADE, verbose_name='类型', help_text='类型')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, null=True, blank=True, verbose_name='中心', help_text='中心')
    is_cancel = models.BooleanField(default=False, verbose_name='是否停用', help_text='是否停用')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-LABEL-标签'
        verbose_name_plural = verbose_name
        db_table = 'crm_label'

    def __str__(self):
        return str(self.id)


class LogLabelCategory(models.Model):
    obj = models.ForeignKey(LabelCategory, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')


    class Meta:
        verbose_name = 'CRM-LABEL-标签类型-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_category_logging'

    def __str__(self):
        return str(self.id)


class LogLabel(models.Model):
    obj = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-LABEL-标签-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_logging'

    def __str__(self):
        return str(self.id)


class LabelCustomerOrder(models.Model):
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
    name = models.CharField(max_length=200, unique=True, db_index=True, verbose_name='标签关联单名称', help_text='标签关联单名称')
    code = models.CharField(max_length=120, unique=True, db_index=True, verbose_name='标签关联单编码', help_text='标签关联单编码')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
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
        verbose_name = 'CRM-LABEL-标签关联单'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer_order'

    def __str__(self):
        return str(self.id)


class LabelCustomerOrderDetails(models.Model):
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
    order = models.ForeignKey(LabelCustomerOrder, on_delete=models.CASCADE, verbose_name='源单', help_text='源单')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
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
        verbose_name = 'CRM-LABEL-标签关联单明细'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer_order_details'

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


class LabelCustomer(models.Model):
    ORDERSTATUS = (
        (0, '失效'),
        (1, '有效'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, verbose_name='中心', help_text='中心')
    order_status = models.SmallIntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-LABEL-客户标签档案'
        unique_together = (("customer", "label"),)
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer'

    def __str__(self):
        return str(self.id)


class LogLabelCustomerOrder(models.Model):
    obj = models.ForeignKey(LabelCustomerOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-LABEL-标签关联单-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer_order_logging'

    def __str__(self):
        return str(self.id)


class LogLabelCustomer(models.Model):
    obj = models.ForeignKey(LabelCustomer, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-LABEL-客户标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer_logging'

    def __str__(self):
        return str(self.id)


class LogLabelCustomerOrderDetails(models.Model):
    obj = models.ForeignKey(LabelCustomerOrderDetails, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-LABEL-标签关联单明细-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_label_customer_order_details_logging'

    def __str__(self):
        return str(self.id)













