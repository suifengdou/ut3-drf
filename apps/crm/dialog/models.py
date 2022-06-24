# coding: utf8
from django.db import models
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.base.warehouse.models import Warehouse
from apps.base.goods.models import Goods
from apps.crm.customers.models import Customer
from apps.utils.geography.models import City
from apps.base.shop.models import Shop


from apps.auth.users.models import UserProfile


class Servicer(models.Model):
    CATEGORY = (
        (0, '机器人'),
        (1, '人工'),
    )
    name = models.CharField(max_length=150, verbose_name='昵称')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺')
    username = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True, verbose_name='人名')
    category = models.SmallIntegerField(choices=CATEGORY, default=1, verbose_name='客服类型')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-对话-客服网名'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_servicer'

    def __str__(self):
        return self.name

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["name", "shop", "username", "category"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class DialogTag(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '正常'),
    )

    CATEGORY = (
        (0, '无法定义'),
        (1, '售前'),
        (2, '售后'),
    )
    name = models.CharField(max_length=30, verbose_name='标签名')
    category = models.SmallIntegerField(choices=CATEGORY, default=0, verbose_name='标签类型')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-对话-标签'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_tag'

    def __str__(self):
        return self.name


class DialogTB(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '正常'),
    )
    shop = models.CharField(max_length=60, verbose_name='店铺', db_index=True)
    customer = models.CharField(max_length=150, verbose_name='客户', db_index=True)
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    min = models.IntegerField(verbose_name='总人次')
    dialog_tag = models.ForeignKey(DialogTag, on_delete=models.CASCADE, null=True, blank=True, verbose_name='对话标签')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', db_index=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-淘系对话-客户'
        unique_together = ('shop', 'customer')
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_taobao'


    def __str__(self):
        return self.customer


class DialogTBDetail(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '未过滤'),
        (2, '未分词'),
    )

    STATUS = (
        (0, '顾客'),
        (1, '客服'),
        (2, '机器人'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复递交，已存在输出单据'),
        (2, '对话的格式错误'),
        (3, '收货人手机地址顺序错误或者手机错误'),
        (4, '地址无法提取省市区'),
        (5, '地址是集运仓'),
        (6, '输出单保存出错'),
        (7, 'UT中不存在此货品'),
        (8, '货品错误'),
        (9, '明细中货品重复'),
        (10, '货品输出单保存出错'),
        (11, '差价必要信息缺失'),
        (12, '差价类型只能填1或3'),
        (13, '差价验算公式错误'),
        (14, '差价验算结果和差价不等'),
        (15, '保存差价申请单出错'),
        (16, '被丢弃'),
    )
    CATEGORY = (
        (0, '常规'),
        (1, '订单'),
        (2, '差价'),
    )

    dialog = models.ForeignKey(DialogTB, on_delete=models.CASCADE, verbose_name='对话')
    sayer = models.CharField(max_length=150, verbose_name='讲话者', db_index=True)
    d_status = models.SmallIntegerField(choices=STATUS, default=0,verbose_name='角色')
    time = models.DateTimeField(verbose_name='时间', db_index=True)
    interval = models.IntegerField(verbose_name='对话间隔(秒)')
    content = models.TextField(verbose_name='内容')

    index_num = models.IntegerField(default=0, verbose_name='对话负面指数')

    erp_order_id = models.CharField(max_length=60, null=True, blank=True, unique=True, verbose_name='原始单号',
                                    help_text='原始单号')

    category = models.SmallIntegerField(choices=CATEGORY, default=0, db_index=True, verbose_name='内容类型')
    extract_tag = models.BooleanField(default=False, verbose_name='是否提取订单', db_index=True)
    sensitive_tag = models.BooleanField(default=False, verbose_name='是否过滤')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, db_index=True, verbose_name='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-淘系对话-信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_taobao_detail'
        permissions = (
            # (权限，权限描述),
            ('view_user_dialogtbdetail', 'Can view user CRM-淘系对话-信息-用户'),
            ('view_handler_dialogtbdetail', 'Can view handler WOP-淘系对话-信息-处理'),
        )

    def __str__(self):
        return self.sayer


class DialogTBWords(models.Model):
    dialog_detail = models.ForeignKey(DialogTBDetail, on_delete=models.CASCADE, verbose_name="对话")
    words = models.CharField(max_length=10, unique=True, verbose_name='分词')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')


    class Meta:
        verbose_name = 'CRM-淘系对话-分词'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_taobao_detail_words'

    def __str__(self):
        return self.words


class DialogJD(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '正常'),
    )

    shop = models.CharField(max_length=60, verbose_name='店铺', db_index=True)
    customer = models.CharField(max_length=150, verbose_name='客户', db_index=True)
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    min = models.IntegerField(verbose_name='总人次')
    dialog_tag = models.ForeignKey(DialogTag, on_delete=models.CASCADE, null=True, blank=True, verbose_name='对话标签')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', db_index=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-京东对话-客户'
        unique_together = ('shop', 'customer')
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_jd'


    def __str__(self):
        return self.customer


class DialogJDDetail(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '未过滤'),
        (2, '未分词'),
    )
    STATUS = (
        (0, '顾客'),
        (1, '客服'),
        (2, '机器人'),
    )
    LOGICAL_DECISION = (
        (0, '否'),
        (1, '是'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复建单'),
        (2, '无补寄原因'),
        (3, '非赠品必填项错误'),
        (4, '店铺错误'),
        (5, '手机错误'),
        (6, '地址无法提取省市区'),
        (7, '地址是集运仓'),
        (8, '输出单保存出错'),
        (9, '货品错误'),
        (10, '明细中货品重复'),
        (11, '输出单保存出错'),
        (12, '被丢弃'),
    )
    CATEGORY = (
        (0, '常规'),
        (1, '订单'),
    )

    dialog = models.ForeignKey(DialogJD, on_delete=models.CASCADE, verbose_name='对话')
    sayer = models.CharField(max_length=150, verbose_name='讲话者', db_index=True)
    d_status = models.SmallIntegerField(choices=STATUS, default=0, verbose_name='角色')
    time = models.DateTimeField(verbose_name='时间', db_index=True)
    interval = models.IntegerField(verbose_name='对话间隔(秒)')
    content = models.TextField(verbose_name='内容')

    index_num = models.IntegerField(default=0, verbose_name='对话负面指数')

    category = models.SmallIntegerField(choices=CATEGORY, default=0, db_index=True, verbose_name='内容类型')
    erp_order_id = models.CharField(max_length=60, null=True, blank=True, unique=True, verbose_name='原始单号',
                                    help_text='原始单号')

    extract_tag = models.SmallIntegerField(choices=LOGICAL_DECISION, default=0, verbose_name='是否提取订单', db_index=True)
    sensitive_tag = models.SmallIntegerField(choices=LOGICAL_DECISION, default=0, verbose_name='是否过滤')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', db_index=True)
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-京东对话-信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_jd_detail'
        permissions = (
            # (权限，权限描述),
            ('view_user_dialogjddetail', 'Can view user CRM-京东对话-信息-用户'),
            ('view_handler_dialogjddetail', 'Can view handler WOP-京东对话-信息-处理'),
        )

    def __str__(self):
        return self.sayer


class DialogJDWords(models.Model):
    dialog_detail = models.ForeignKey(DialogJDDetail, on_delete=models.CASCADE, verbose_name="对话")
    words = models.CharField(max_length=10, unique=True, verbose_name='分词')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-京东对话-分词'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_jd_detail_words'

    def __str__(self):
        return self.words


class DialogOW(models.Model):
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复建单'),
        (2, '无补寄原因'),
        (3, '非赠品必填项错误'), m
        (4, '店铺错误'),
        (5, '手机错误'),
        (6, '地址无法提取省市区'),
        (7, '地址是集运仓'),
        (8, '输出单保存出错'),
        (9, '货品错误'),
        (10, '明细中货品重复'),
        (11, '输出单保存出错'),
        (12, '被丢弃'),
    )

    ORDER_STATUS = (
        (0, '被取消'),
        (1, '未过滤'),
        (2, '未分词'),
    )

    call_id = models.CharField(max_length=60, unique=True, verbose_name='会话ID', help_text='会话ID')
    guest_entry_time = models.CharField(max_length=60, verbose_name='访客进入时间', help_text='访客进入时间')
    call_start_time = models.CharField(max_length=60, verbose_name='会话开始时间', help_text='会话开始时间')
    first_response_time = models.CharField(max_length=60, verbose_name='客服首次响应时长', help_text='客服首次响应时长')
    average_response_time = models.CharField(max_length=60, verbose_name='客服平均响应时长', help_text='客服平均响应时长')
    queue_time = models.CharField(max_length=60, verbose_name='访客排队时长', help_text='访客排队时长')
    call_duration = models.CharField(max_length=60, verbose_name='会话时长', help_text='会话时长')
    ender = models.CharField(max_length=60, verbose_name='会话终止方', help_text='会话终止方')
    call_status = models.CharField(max_length=60, verbose_name='客服解决状态', help_text='客服解决状态')
    primary_classification = models.CharField(max_length=60, null=True, blank=True, verbose_name='一级分类', help_text='一级分类')
    secondary_classification = models.CharField(max_length=60, null=True, blank=True, verbose_name='二级分类', help_text='二级分类')
    three_level_classification = models.CharField(max_length=60, null=True, blank=True, verbose_name='三级分类', help_text='三级分类')
    four_level_classification = models.CharField(null=True, blank=True, max_length=60, verbose_name='四级分类', help_text='四级分类')
    five_level_classification = models.CharField(null=True, blank=True, max_length=60, verbose_name='五级分类', help_text='五级分类')
    servicer = models.CharField(max_length=60, null=True, blank=True, verbose_name='接待客服', help_text='接待客服')
    customer = models.CharField(max_length=60, null=True, blank=True, verbose_name='访客用户名', help_text='访客用户名')
    satisfaction = models.CharField(max_length=60, null=True, blank=True, verbose_name='满意度', help_text='满意度')
    rounds = models.CharField(max_length=60, null=True, blank=True, verbose_name='对话回合数', help_text='对话回合数')
    source = models.CharField(max_length=60, null=True, blank=True, verbose_name='来源终端', help_text='来源终端')
    goods_type = models.CharField(max_length=60, null=True, blank=True, verbose_name='产品型号', help_text='产品型号')
    purchase_time = models.CharField(max_length=60, null=True, blank=True, verbose_name='购买日期', help_text='购买日期')

    shop = models.CharField(max_length=60, null=True, blank=True, verbose_name='购买店铺', help_text='购买店铺')
    area = models.CharField(max_length=60, null=True, blank=True, verbose_name='省市区', help_text='省市区')
    m_sn = models.CharField(max_length=60, null=True, blank=True, verbose_name='出厂序列号', help_text='出厂序列号')
    address = models.CharField(max_length=60, null=True, blank=True, verbose_name='详细地址', help_text='详细地址')
    order_category = models.CharField(max_length=60, null=True, blank=True, verbose_name='补寄原因', help_text='补寄原因')
    goods_details = models.CharField(max_length=200, null=True, blank=True, verbose_name='配件信息', help_text='配件信息')
    broken_part = models.CharField(max_length=50, null=True, blank=True, verbose_name='损坏部位', help_text='损坏部位')
    description = models.CharField(max_length=200, null=True, blank=True, verbose_name='损坏描述', help_text='损坏描述')
    mobile = models.CharField(max_length=60, null=True, blank=True, verbose_name='建单手机', help_text='建单手机')
    receiver = models.CharField(max_length=60, null=True, blank=True, verbose_name='收件人姓名', help_text='收件人姓名')

    is_order = models.BooleanField(default=False, db_index=True, verbose_name='是否建配件工单', help_text='是否建配件工单')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', db_index=True)
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')
    erp_order_id = models.CharField(max_length=60, null=True, blank=True, unique=True, verbose_name='原始单号',
                                    help_text='原始单号')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-官网对话-客户'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_official'
        permissions = (
            # (权限，权限描述),
            ('view_user_dialogow', 'Can view user CRM-官网对话-用户'),
            ('view_handler_dialogow', 'Can view handler WOP-官网对话-处理'),
        )

    def __str__(self):
        return self.customer

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["call_id", "guest_entry_time", "call_start_time", "first_response_time",
                        "average_response_time", "queue_time", "call_duration", "ender", "call_status",
                        "primary_classification", "secondary_classification", "three_level_classification",
                        "four_level_classification", "five_level_classification", "servicer", "customer",
                        "satisfaction", "rounds", "source", "content", "goods_type", "purchase_time",
                        "shop", "area", "m_sn", "address", "order_category", "goods_details", "broken_part",
                        "description", "mobile", "receiver"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class DialogOWDetail(models.Model):
    ORDER_STATUS = (
        (0, '被取消'),
        (1, '正常'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '对话格式错误'),
        (2, '重复导入'),
    )
    CATEGORY = (
        (0, '常规'),
        (1, '订单'),
    )
    STATUS = (
        (0, '顾客'),
        (1, '客服'),
        (2, '机器人'),
    )

    dialog = models.ForeignKey(DialogOW, on_delete=models.CASCADE, verbose_name='对话')
    sayer = models.CharField(max_length=150, verbose_name='讲话者', db_index=True)
    time = models.DateTimeField(verbose_name='时间', db_index=True)
    interval = models.IntegerField(verbose_name='对话间隔(秒)')
    content = models.TextField(verbose_name='内容')

    index_num = models.IntegerField(default=0, verbose_name='对话负面指数')
    d_status = models.SmallIntegerField(choices=STATUS, default=0, verbose_name='角色')
    category = models.BooleanField(choices=CATEGORY, default=0, verbose_name='内容类型')
    extract_tag = models.BooleanField(default=False, verbose_name='是否提取订单')
    sensitive_tag = models.BooleanField(default=False, verbose_name='是否过滤')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', db_index=True)
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-官网对话-信息'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_official_detail'

    def __str__(self):
        return self.sayer


class DialogOWWords(models.Model):
    dialog_detail = models.ForeignKey(DialogOWDetail, on_delete=models.CASCADE, verbose_name="对话")
    words = models.CharField(max_length=10, unique=True, verbose_name='分词')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-官网对话-分词'
        verbose_name_plural = verbose_name
        db_table = 'crm_dialog_official_detail_words'

    def __str__(self):
        return self.words
