from django.db import models
import django.utils.timezone as timezone

from apps.base.department.models import Department
from apps.auth.users.models import UserProfile


class TodoList(models.Model):
    ORDER_STATUS = (
        (0, '已取消'),
        (1, '待完成'),
        (2, '已完成'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '已处理'),
    )

    name = models.CharField(unique=True, max_length=100, verbose_name='事务名', help_text='事务名')
    done = models.BooleanField(default=False, verbose_name='是否在做', help_text='是否在做')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='事务状态', help_text='事务状态')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='账号', help_text='账号')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'Utils-TodoList'
        verbose_name_plural = verbose_name
        db_table = 'utils_todolist'

    def __str__(self):
        return self.name

