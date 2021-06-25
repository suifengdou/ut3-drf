from django.db import models
from apps.auth.users.models import UserProfile
import django.utils.timezone as timezone
import pandas as pd


class Account(models.Model):
    ORDER_STATUS = (
        (0, '已冻结'),
        (1, '正常'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '账户异常'),
    )

    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, verbose_name='关联用户', help_text='关联用户')
    name = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='账户名称', help_text='账户名称')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='冻结原因', help_text='冻结原因')

    class Meta:
        verbose_name = 'SALES-预付-账户管理'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_account'
        permissions = (
            ('view_user_account', 'Can view user SALES-预付-账户管理'),
        )

    def __str__(self):
        return self.name


class Statements(models.Model):

    CATEGORY = (
        (0, '支出'),
        (1, '预存'),
        (2, '退款'),
    )

    order_id = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='流水号', help_text='流水号')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='关联账户')
    category = models.IntegerField(choices=CATEGORY, default=0, verbose_name='类型', help_text='类型')
    revenue = models.FloatField(default=0, verbose_name='入账', help_text='入账')
    expenses = models.FloatField(default=0, verbose_name='支出', help_text='支出')
    memorandum = models.CharField(max_length=200, verbose_name='备注', help_text='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    check_status = models.BooleanField(default=False, verbose_name='验算状态', help_text='验算状态')

    class Meta:
        verbose_name = 'SALES-预付-流水明细'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_statements'
        permissions = (
            ('view_user_statement', 'Can view user SALES-预付-流水明细'),
        )

    def __str__(self):
        return self.order_id


class Prestore(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '未提交'),
        (2, '待审核'),
        (3, '已入账'),
        (4, '已清账'),
    )
    CATEGORY = (
        (1, '预存'),
        (2, '退款'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '流水号重复'),
        (2, '反馈信息为空'),
        (3, '预存不可重复审核'),
        (4, '保存流水出错'),
        (5, '保存验证出错'),
    )

    order_id = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='预存号', help_text='预存号')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='关联账户')
    bank_sn = models.CharField(unique=True, max_length=100, verbose_name='流水号', help_text='流水号')
    category = models.IntegerField(choices=CATEGORY, default=1, verbose_name='类型', help_text='类型')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    amount = models.FloatField(default=0, verbose_name='存入金额', help_text='存入金额')
    remaining = models.FloatField(default=0, verbose_name='可用金额', help_text='可用金额')
    memorandum = models.CharField(max_length=200, verbose_name='备注', help_text='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    feedback = models.CharField(max_length=150, blank=True, null=True, verbose_name='反馈内容', help_text='反馈内容')

    class Meta:
        verbose_name = 'SALES-预付-预存管理'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_prestore'
        permissions = (
            ('view_user_prestore', 'Can view user SALES-预付-预存管理'),
        )

    def __str__(self):
        return self.order_id


class Expense(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待结算'),
        (2, '已清账'),
    )
    CATEGORY = (
        (0, '支出'),
    )

    order_id = models.CharField(unique=True, max_length=30, db_index=True, verbose_name='支出号', help_text='支出号')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='关联账户')
    category = models.IntegerField(choices=CATEGORY, default=0, verbose_name='类型', help_text='类型')
    order_status = models.IntegerField(choices=ORDER_STATUS, default=1, verbose_name='状态', help_text='状态')
    amount = models.FloatField(default=0, verbose_name='支出金额', help_text='支出金额')
    memorandum = models.CharField(max_length=200, verbose_name='备注', help_text='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-预付-支出管理'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_expense'

    def __str__(self):
        return self.order_id


class VerificationPrestore(models.Model):
    prestore = models.ForeignKey(Prestore, on_delete=models.CASCADE, verbose_name='关联预存', help_text='关联预存')
    statement = models.ForeignKey(Statements, on_delete=models.CASCADE, verbose_name='关联流水', help_text='关联流水')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-预付-预存校验'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_verifyprestore'

    def __str__(self):
        return self.id


class VerificationExpenses(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, verbose_name='关联支出', help_text='关联支出')
    statement = models.ForeignKey(Statements, on_delete=models.CASCADE, verbose_name='关联流水', help_text='关联流水')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'SALES-预付-支出校验'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_verifyexpense'

    def __str__(self):
        return self.id


class ExpendList(models.Model):
    statements = models.ForeignKey(Statements, on_delete=models.CASCADE, verbose_name='关联支出', help_text='关联支出')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='关联账户')
    prestore = models.ForeignKey(Prestore, on_delete=models.CASCADE, verbose_name='关联预存', help_text='关联预存')
    amount = models.FloatField(default=0, verbose_name='实际冲减金额', help_text='实际冲减金额')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')


    class Meta:
        verbose_name = 'SALES-预付-余额校验'
        verbose_name_plural = verbose_name
        db_table = 'sales_ap_expendlist'

    def __str__(self):
        return self.id