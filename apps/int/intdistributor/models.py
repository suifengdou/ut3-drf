from django.db import models
from apps.base.company.models import Company
from apps.utils.geography.models import Nationality
from django.contrib.auth import get_user_model
User = get_user_model()
from apps.base.department.models import Department
from apps.utils.geography.models import Nationality


# Create your models here.


class IntDistributor(models.Model):
    CATEGORY_LIST = (
        (1, '商业'),
        (2, '终端'),
        (3, '全渠道'),
    )
    STATUS_LIST = (
        (0, '已取消'),
        (1, '正常'),
    )

    name = models.CharField(unique=True, max_length=150, db_index=True, verbose_name='经销商', help_text='经销商')
    d_id = models.CharField(unique=True, max_length=60, null=True, blank=True, verbose_name='经销商ID', help_text='经销商ID')
    source = models.CharField(max_length=60, verbose_name='来源', help_text='来源')
    category = models.IntegerField(choices=CATEGORY_LIST, default=1, verbose_name='经销商类型', help_text='经销商类型')
    nationality = models.ForeignKey(Nationality, on_delete=models.CASCADE, verbose_name='国别', help_text='国别')
    website = models.CharField(max_length=230, null=True, blank=True, verbose_name='网站', help_text='网站')
    email = models.CharField(max_length=60, null=True, blank=True, verbose_name='邮箱', help_text='邮箱')
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name='地址', help_text='地址')
    phone = models.CharField(max_length=60, verbose_name='电话', help_text='电话')

    order_status = models.IntegerField(choices=STATUS_LIST, default=1, verbose_name='经销商状态', help_text='经销商状态')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='部门', help_text='部门')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')

    class Meta:
        verbose_name = 'INT-国际经销商'
        verbose_name_plural = verbose_name
        db_table = 'int_distributor'
        permissions = (
            # (权限，权限描述),
            ('view_user_intdistributor', 'Can view intdistributor INT-国际经销商'),
        )

    def __str__(self):
        return self.name


class Contacts(models.Model):

    GENDER_LIST = (
        (1, '男'),
        (2, '女'),
    )
    distributor = models.ForeignKey(IntDistributor, on_delete=models.CASCADE, verbose_name='经销商', help_text='经销商')
    name = models.CharField(unique=True, max_length=200, db_index=True, verbose_name='联系人', help_text='联系人')
    position = models.CharField(null=True, blank=True, max_length=90, verbose_name='职位', help_text='职位')
    gender = models.IntegerField(choices=GENDER_LIST, default=1, verbose_name='性别', help_text='性别')
    is_staff = models.BooleanField(default=True, verbose_name='在职状态', help_text='在职状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际经销商-联系人'
        verbose_name_plural = verbose_name
        db_table = 'int_distributor_contacts'

    def __str__(self):
        return self.name


class ContactMode(models.Model):
    contacts = models.ForeignKey(Contacts, on_delete=models.CASCADE, verbose_name='联系人', help_text='联系人')
    name = models.CharField(max_length=150, verbose_name='联系方式', help_text='联系方式')
    content = models.CharField(max_length=150, verbose_name='相关内容', help_text='职位')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'INT-国际经销商-联系人-方式'
        verbose_name_plural = verbose_name
        db_table = 'int_distributor_contacts_mode'

    def __str__(self):
        return self.name


