# -*- coding: utf-8 -*-
# @Time    : 2020/09/17 13:47
# @Author  : Hann
# @Site    :
# @File    : urls.py.py
# @Software: PyCharm

from django.db import models
from django.db.models import Sum, Avg, Min, Max, F
import django.utils.timezone as timezone
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.crm.dialog.models import DialogTBDetail


class Compensation(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    ORDER_CATEGORY = (
        (1, '差价补偿'),
        (2, '错误重置'),
        (3, '退货退款'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复建单'),
        (2, '特殊订单才能追加'),
        (3, '追加单保存出错'),
        (4, '实收减应收不等于校验金额'),
        (5, '差价金额不等于校验金额'),
        (6, '恢复单保存出错'),
        (7, '补偿单保存出错'),
        (8, '相同单号存在多个差价，需要设置特殊订单'),
        (9, '相同单号存在多个差价，需要设置特殊订单'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '特殊订单'),
        (3, '重置订单'),
    )
    servicer = models.CharField(max_length=50, verbose_name='客服', help_text='客服')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    nickname = models.CharField(max_length=50, db_index=True, verbose_name='用户网名', help_text='用户网名')
    order_id = models.CharField(max_length=60, db_index=True, verbose_name='订单号', help_text='订单号')
    order_category = models.SmallIntegerField(choices=ORDER_CATEGORY, default=1, verbose_name='单据类型', help_text='单据类型')
    compensation = models.FloatField(verbose_name='补偿金额', help_text='补偿金额')
    name = models.CharField(max_length=150, db_index=True, verbose_name='姓名', help_text='姓名')
    alipay_id = models.CharField(max_length=150, db_index=True, verbose_name='支付宝', help_text='支付宝')
    actual_receipts = models.FloatField(verbose_name='实收金额', help_text='实收金额')
    receivable = models.FloatField(verbose_name='应收金额', help_text='应收金额')
    checking = models.FloatField(verbose_name='验算结果', help_text='验算结果')
    memorandum = models.TextField(blank=True, null=True, verbose_name='备注', help_text='备注')

    erp_order_id = models.CharField(max_length=60, null=True, blank=True, unique=True, verbose_name='UT订单号', help_text='UT订单号')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.IntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='错误列表')
    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='处理人', help_text='处理人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间', help_text='处理时间')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-补偿单'
        verbose_name_plural = verbose_name
        db_table = 'dfc_compensation'

    def __str__(self):
        return str(self.alipay_id)


class BatchCompensation(models.Model):

    ORDER_CATEGORY = (
        (1, '差价补偿'),
        (2, '错误重置'),
        (3, '退货退款'),
    )

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未结算'),
        (3, '已完成'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '无OA单号'),
        (2, '先设置订单已完成再审核'),
        (3, '已递交过此OA单号'),
        (4, '补寄配件记录格式错误'),
        (5, '补寄原因错误'),
        (6, '单据创建失败'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已确认'),
        (2, '特殊订单'),
    )
    order_id = models.CharField(max_length=60, db_index=True, verbose_name='批次单号', help_text='创建时间')
    oa_order_id = models.CharField(null=True, blank=True, max_length=60, verbose_name='OA单号', help_text='创建时间')
    order_category = models.SmallIntegerField(choices=ORDER_CATEGORY, default=1, verbose_name='单据类型', help_text='单据类型')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='单据状态', help_text='创建时间')
    process_tag = models.IntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签', help_text='创建时间')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表', help_text='创建时间')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-补偿汇总单'
        verbose_name_plural = verbose_name
        db_table = 'dfc_compensation_batch'

    def __str__(self):
        return str(self.order_id)


class BCDetail(models.Model):
    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '未结算'),
        (3, '已完成'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '已付金额不是零，不可重置'),
        (2, '重置保存补偿单出错'),
        (3, '补运费和已付不相等'),
        (4, '补寄配件记录格式错误'),
        (5, '补寄原因错误'),
        (6, '单据创建失败'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '已处理'),
        (2, '特殊订单'),
    )

    batch_order = models.ForeignKey(BatchCompensation, on_delete=models.CASCADE, verbose_name='批次单')
    compensation_order = models.OneToOneField(Compensation, on_delete=models.CASCADE, verbose_name='补偿单')
    servicer = models.CharField(max_length=50, verbose_name='客服')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    nickname = models.CharField(max_length=50, verbose_name='用户网名', db_index=True)
    order_id = models.TextField(verbose_name='订单号')
    compensation = models.FloatField(verbose_name='补偿金额')
    paid_amount = models.FloatField(default=0, verbose_name='已付金额')
    name = models.CharField(max_length=150, verbose_name='姓名', db_index=True)
    alipay_id = models.CharField(max_length=150, verbose_name='支付宝', db_index=True)
    actual_receipts = models.FloatField(verbose_name='实收金额')
    receivable = models.FloatField(verbose_name='应收金额')
    checking = models.FloatField(verbose_name='验算结果')
    memorandum = models.TextField(blank=True, null=True, verbose_name='备注')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='处理人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')

    process_tag = models.IntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')
    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, verbose_name='单据状态')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'DFC-补偿汇总明细单'
        verbose_name_plural = verbose_name
        db_table = 'dfc_compensation_batch_detail'

    def __str__(self):
        return str(self.batch_order)



