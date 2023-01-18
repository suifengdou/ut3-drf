from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.utils.geography.models import Province, City, District
from apps.base.goods.models import Goods
from apps.auth.users.models import UserProfile


class Customer(models.Model):

    name = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='会员名')
    memo = models.CharField(null=True, blank=True, max_length=30, verbose_name='备注')

    class Meta:
        verbose_name = 'CRM-C-客户信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer'

    def __str__(self):
        return str(self.name)


class Address(models.Model):

    S_SOURCE = (
        (1, '用户体验工单'),
    )
    source_id = models.CharField(unique=True, max_length=150, verbose_name='来源单号', help_text='来源单号')
    source = models.SmallIntegerField(choices=S_SOURCE, default=1, verbose_name='来源', help_text='来源')

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    name = models.CharField(max_length=150, db_index=True, verbose_name='姓名', help_text='姓名')
    smartphone = models.CharField(max_length=30, db_index=True, verbose_name='手机', help_text='手机')
    address = models.CharField(max_length=250, verbose_name='地址', help_text='地址')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省份', help_text='省份')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='城市', help_text='城市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, verbose_name='区县', help_text='区县')
    is_default = models.BooleanField(default=True, verbose_name='是否默认', help_text='是否默认')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-C-客户信息-地址信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_address'

    def __str__(self):
        return str(self.name)


class Money(models.Model):

    S_SOURCE = (
        (1, '用户体验工单'),
    )
    CATEGORY_LIST = (
        (1, '收入'),
        (2, '支出'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    source_id = models.CharField(unique=True, max_length=150, verbose_name='来源单号', help_text='来源单号')
    source = models.SmallIntegerField(choices=S_SOURCE, default=1, verbose_name='来源', help_text='来源')
    category = models.SmallIntegerField(choices=CATEGORY_LIST, default=1, verbose_name='类别', help_text='类别')
    amount = models.FloatField(default=0, verbose_name='金额', help_text='金额')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-C-客户信息-钱'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_money'

    def __str__(self):
        return str(self.amount)


class CustomerGoods(models.Model):
    S_SOURCE = (
        (1, '用户体验工单'),
    )
    CATEGORY_LIST = (
        (1, '商品'),
        (2, '赠品'),
        (3, '售后'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')
    source_id = models.CharField(unique=True, max_length=150, verbose_name='来源单号', help_text='来源单号')
    category = models.SmallIntegerField(choices=CATEGORY_LIST, default=1, verbose_name='类别', help_text='类别')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    purchased_time = models.DateTimeField(null=True, blank=True, verbose_name='购买时间', help_text='购买时间')
    m_sn = models.CharField(null=True, blank=True, max_length=250, verbose_name='SN', help_text='SN')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-C-客户信息-货'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_goods'

    def __str__(self):
        return str(self.goods.name)


class LogCustomer(models.Model):
    obj = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-C-客户信息-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_logging'

    def __str__(self):
        return str(self.id)


class LogAddress(models.Model):
    obj = models.ForeignKey(Address, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-C-客户信息-地址信息-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_address_logging'

    def __str__(self):
        return str(self.id)


class LogMoney(models.Model):
    obj = models.ForeignKey(Money, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-C-客户信息-钱-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_money_logging'

    def __str__(self):
        return str(self.id)


class LogCustomerGoods(models.Model):
    obj = models.ForeignKey(CustomerGoods, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-C-客户信息-货-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_customer_goods_logging'

    def __str__(self):
        return str(self.id)

