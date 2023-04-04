from django.db import models

# Create your models here.
from apps.crm.customers.models import Customer
from apps.auth.users.models import UserProfile
from apps.crm.labels.models import Label


class CustomerLabelPerson(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-PERSON-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_person'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelPerson(models.Model):
    obj = models.ForeignKey(CustomerLabelPerson, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-PERSON-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_person_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelFamily(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-FAMILY-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_family'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelFamily(models.Model):
    obj = models.ForeignKey(CustomerLabelFamily, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-FAMILY-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_family_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelProduct(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-PRODUCT-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_product'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelProduct(models.Model):
    obj = models.ForeignKey(CustomerLabelProduct, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-PRODUCT-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_product_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelOrder(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-ORDER-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_order'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelOrder(models.Model):
    obj = models.ForeignKey(CustomerLabelOrder, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-ORDER-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_order_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelService(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-SERVICE-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_service'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelService(models.Model):
    obj = models.ForeignKey(CustomerLabelService, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-SERVICE-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_service_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelSatisfaction(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-SATISFACTION-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_satisfaction'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelSatisfaction(models.Model):
    obj = models.ForeignKey(CustomerLabelSatisfaction, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-SATISFACTION-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_satisfaction_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelRefund(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-REFUND-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_refund'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelRefund(models.Model):
    obj = models.ForeignKey(CustomerLabelRefund, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-REFUND-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_refund_logging'

    def __str__(self):
        return str(self.id)


class CustomerLabelOthers(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    label = models.ForeignKey(Label, on_delete=models.CASCADE, verbose_name='标签', help_text='标签')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-OTHERS-标签档案'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_others'

    def __str__(self):
        return str(self.id)


class LogCustomerLabelOthers(models.Model):
    obj = models.ForeignKey(CustomerLabelOthers, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-CUSTOMER-LABEL-OTHERS-标签档案-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_label_others_logging'

    def __str__(self):
        return str(self.id)
