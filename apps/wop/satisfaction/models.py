
from django.db import models
import django.utils.timezone as timezone

from apps.base.company.models import Company
from apps.base.goods.models import Goods
from apps.crm.customers.models import Customer, Address, ContactAccount, Money, Interaction
from apps.utils.geography.models import Province, City, District
from apps.base.department.models import Department
from apps.auth.users.models import UserProfile
from apps.crm.vipwechat.models import Specialist



class OriSatisfactionWorkOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待递交'),
        (2, '递交完成'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复提交，点击修复工单'),
        (2, '已存在未完结工单，联系处理同学追加问题'),
        (3, '地址无法提取省市区'),
        (4, '创建体验单错误'),
        (5, '初始化体验单失败'),
        (6, '初始化体验单资料失败'),
        (7, '体验单已操作无法修复'),
    )

    order_id = models.CharField(unique=True, null=True, blank=True, max_length=100, verbose_name='原始工单编号', help_text='原始工单编号')
    title = models.CharField(max_length=120, verbose_name='原始工单标题', help_text='原始工单标题')
    nickname = models.CharField(max_length=120, verbose_name='用户ID', help_text='用户ID')
    mobile = models.CharField(max_length=60, db_index=True, verbose_name='接洽电话', help_text='接洽电话')
    purchase_time = models.DateTimeField(verbose_name='购买时间', help_text='购买时间')
    purchase_interval = models.IntegerField(null=True, blank=True, verbose_name='购买时长', help_text='购买时长')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称', help_text='货品名称')
    quantity = models.IntegerField(null=True, blank=True, verbose_name='货品数量', help_text='货品数量')
    m_sn = models.CharField(null=True, blank=True, max_length=60, verbose_name='机器SN', help_text='机器SN')

    receiver = models.CharField(max_length=150, verbose_name='客户姓名', help_text='客户姓名')
    address = models.CharField(max_length=150, verbose_name='客户地址', help_text='客户地址')

    is_friend = models.BooleanField(default=False, verbose_name='是否微友', help_text='是否微友')
    cs_wechat = models.CharField(null=True, blank=True, max_length=150, verbose_name='微信ID', help_text='微信ID')

    demand = models.CharField(max_length=150, verbose_name='诉求', help_text='诉求')
    information = models.TextField(verbose_name='问题描述', help_text='问题描述')


    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-原始用户体验工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_ori'

    def __str__(self):
        return str(self.id)


class OSWOFiles(models.Model):
    name = models.CharField(max_length=150, verbose_name='文件名称', help_text='文件名称')
    suffix = models.CharField(max_length=100, verbose_name='文件类型', help_text='文件类型')
    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(OriSatisfactionWorkOrder, on_delete=models.CASCADE, verbose_name='原始体验工单', help_text='原始体验工单')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-原始用户体验工单-文档'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_ori_files'
        permissions = (
            # (权限，权限描述),
            ('view_handle_orisatisfactionworkorder', 'Can view handle WOP-原始用户体验工单-综合处理'),

        )

    def __str__(self):
        return str(self.id)


class SatisfactionWorkOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待领取'),
        (2, '等待处理'),
        (3, '事务完结'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '已存在已执行服务单，不可创建'),
        (2, '创建服务单错误'),
        (3, '体验单未完成不可审核'),
    )

    PROCESSTAG = (
        (0, '无'),
        (1, '近30天内重复'),
        (2, '近30天外重复'),
        (3, '存在服务单'),
        (4, '存在专属客服'),
        (5, '特殊工单'),
    )

    STAGE_LIST = (
        (1, '初始提交'),
        (2, '处理初期'),
        (3, '处理中期'),
        (4, '处理后期'),
        (5, '处理结束'),
    )

    ori_order = models.OneToOneField(OriSatisfactionWorkOrder, on_delete=models.CASCADE, verbose_name='原始工单', help_text='原始工单')
    order_id = models.CharField(unique=True, max_length=100, verbose_name='工单编号', help_text='工单编号')
    title = models.CharField(max_length=120, verbose_name='工单标题', help_text='工单标题')
    nickname = models.CharField(max_length=120, verbose_name='用户ID', help_text='用户ID')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='用户', help_text='用户')
    purchase_time = models.DateTimeField(verbose_name='购买时间', help_text='购买时间')
    purchase_interval = models.IntegerField(null=True, blank=True, verbose_name='购买时长', help_text='购买时长')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称', help_text='货品名称')
    quantity = models.IntegerField(null=True, blank=True, verbose_name='货品数量', help_text='货品数量')
    m_sn = models.CharField(null=True, blank=True, max_length=60, verbose_name='机器SN', help_text='机器SN')

    receiver = models.CharField(max_length=150, verbose_name='客户姓名', help_text='客户姓名')
    address = models.CharField(max_length=150, verbose_name='客户地址', help_text='客户地址')
    mobile = models.CharField(max_length=60, db_index=True, verbose_name='手机', help_text='手机')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    is_friend = models.BooleanField(default=False, verbose_name='是否微友', help_text='是否微友')
    cs_wechat = models.CharField(null=True, blank=True, max_length=150, verbose_name='微信ID', help_text='微信ID')
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, null=True, blank=True, verbose_name='专属客服', help_text='专属客服')
    demand = models.CharField(max_length=150, verbose_name='诉求', help_text='诉求')

    handler = models.CharField(null=True, blank=True, max_length=30, verbose_name='领取人', help_text='领取人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='领取时间', help_text='领取时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='领取间隔(分钟)', help_text='领取间隔(分钟)')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    stage = models.SmallIntegerField(choices=STAGE_LIST, default=1, verbose_name='进度标签', help_text='进度标签')
    appointment = models.DateTimeField(null=True, blank=True, verbose_name='下次预约', help_text='下次预约')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')

    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    cost = models.FloatField(default=0, verbose_name='服务金额', help_text='服务金额')
    suggestion = models.TextField(null=True, blank=True, max_length=900, verbose_name='处理意见', help_text='处理意见')
    rejection = models.CharField(null=True, blank=True, max_length=260, verbose_name='驳回原因', help_text='驳回原因')

    class Meta:
        verbose_name = 'WOP-用户体验工单'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction'

        permissions = (
            # (权限，权限描述),
            ('view_user_satisfactionworkorder', 'Can view user WOP-用户体验工单-用户'),
            ('view_handler_satisfactionworkorder', 'Can view handler WOP-用户体验工单-处理'),
            ('view_check_satisfactionworkorder', 'Can view check WOP-用户体验工单-审核'),
        )

    def __str__(self):
        return str(self.id)


class SWOProgress(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待确认'),
        (2, '确认完成'),
    )
    STAGE_LIST = (
        (1, '初始提交'),
        (2, '处理初期'),
        (3, '处理中期'),
        (4, '处理后期'),
        (5, '处理结束'),
    )

    order = models.ForeignKey(SatisfactionWorkOrder, on_delete=models.CASCADE, verbose_name='工单', help_text='工单')
    process_id = models.CharField(unique=True, null=True, blank=True, max_length=100, verbose_name='进度编号', help_text='进度编号')
    title = models.CharField(max_length=120, verbose_name='进度标题', help_text='进度标题')
    stage = models.SmallIntegerField(choices=STAGE_LIST, default=1, verbose_name='进度标签', help_text='进度标签')
    appointment = models.DateTimeField(null=True, blank=True, verbose_name='下次预约', help_text='下次预约')
    action =  models.CharField(max_length=120, verbose_name='动作', help_text='动作')
    content = models.TextField(verbose_name='内容', help_text='内容')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', help_text='单据状态')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-用户体验工单-执行单'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_process'

        permissions = (
            # (权限，权限描述),
            ('view_user_swoprogress', 'Can view user WOP-用户体验工单-执行单-用户'),
            ('view_handler_swoprogress', 'Can view handler WOP-用户体验工单-执行单-处理'),
            ('view_check_swoprogress', 'Can view check WOP-用户体验工单-执行单-审核'),
            ('view_audit_swoprogress', 'Can view audit WOP-用户体验工单-执行单-结算'),
        )

    def __str__(self):
        return str(self.id)


class SWOPFiles(models.Model):
    name = models.CharField(max_length=150, verbose_name='文件名称', help_text='文件名称')
    suffix = models.CharField(max_length=100, verbose_name='文件类型', help_text='文件类型')
    url = models.CharField(max_length=250, verbose_name='URL地址', help_text='URL地址')
    workorder = models.ForeignKey(SWOProgress, on_delete=models.CASCADE, verbose_name='进度工单', help_text='进度工单')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-用户体验工单-执行单-文档'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_process_files'

    def __str__(self):
        return str(self.id)


class ServiceWorkOrder(models.Model):

    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '服务执行'),
        (2, '服务完成'),
    )

    MISTAKE_LIST = (
        (0, '正常'),
        (1, '存在未完结发货单'),
        (2, '费用为零不可审核'),
        (3, '不存在费用单不可以审核'),
        (4, '理赔必须设置需理赔才可以审核'),
        (5, '驳回原因为空'),
        (6, '无反馈内容, 不可以审核'),
    )

    PROCESSTAG = (
        (0, '无'),
        (1, '近30天内重复'),
        (2, '近30天外重复'),
    )

    swo_order = models.OneToOneField(SatisfactionWorkOrder, on_delete=models.CASCADE, verbose_name='体验单', help_text='体验单')
    order_id = models.CharField(unique=True, max_length=100, verbose_name='服务编号', help_text='服务编号')
    title = models.CharField(max_length=120, verbose_name='服务标题', help_text='服务标题')
    nickname = models.CharField(max_length=120, verbose_name='用户ID', help_text='用户ID')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='用户', help_text='用户')

    receiver = models.CharField(max_length=150, verbose_name='客户姓名', help_text='客户姓名')
    address = models.CharField(max_length=150, verbose_name='客户地址', help_text='客户地址')
    mobile = models.CharField(max_length=60, db_index=True, verbose_name='手机', help_text='手机')

    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True, verbose_name='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, verbose_name='区')

    demand = models.CharField(max_length=150, verbose_name='诉求', help_text='诉求')

    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')

    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='工单状态', help_text='工单状态')
    cost = models.FloatField(default=0, verbose_name='服务金额', help_text='服务金额')
    quantity = models.IntegerField(default=0, verbose_name='货品总数', help_text='货品总数')
    memo = models.CharField(null=True, blank=True, max_length=250, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-用户体验工单-服务单'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_service'

        permissions = (
            # (权限，权限描述),
            ('view_user_serviceworkorder', 'Can view user WOP-用户体验工单-服务单-用户'),
            ('view_handler_serviceworkorder', 'Can view handler WOP-用户体验工单-服务单-处理'),
            ('view_check_serviceworkorder', 'Can view check WOP-用户体验工单-服务单-审核'),
        )

    def __str__(self):
        return str(self.id)


class InvoiceWorkOrder(models.Model):

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



    swo_order = models.ForeignKey(ServiceWorkOrder, on_delete=models.CASCADE, verbose_name='服务单', help_text='服务单')
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
        verbose_name = 'WOP-用户体验工单-服务单-发货单'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_service_invoice'

        permissions = (
            # (权限，权限描述),
            ('view_user_invoiceworkorder', 'Can view user WOP-用户体验工单-服务单-发货单-用户'),
            ('view_handler_invoiceworkorder', 'Can view handler WOP-用户体验工单-服务单-发货单-处理'),
            ('view_check_invoiceworkorder', 'Can view check WOP-用户体验工单-服务单-发货单-审核'),
        )

    def __str__(self):
        return str(self.id)


class IWOGoods(models.Model):
    CATEGORY = (
        (1, '发出货品'),
        (2, '退回货品'),
        (3, '单纯费用'),
        (4, '单纯收入'),
    )
    invoice = models.ForeignKey(InvoiceWorkOrder, on_delete=models.CASCADE, verbose_name='发货单', help_text='发货单')
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
        verbose_name = 'WOP-用户体验工单-服务单-发货单-货品'
        verbose_name_plural = verbose_name
        unique_together = (('invoice', 'goods_name'))
        db_table = 'wop_satisfaction_service_invoice_goods'

    def __str__(self):
        return str(self.goods_id)


class CheckInvoice(models.Model):
    swo_order = models.ForeignKey(ServiceWorkOrder, on_delete=models.CASCADE, verbose_name='服务单', help_text='服务单')
    invoice = models.OneToOneField(InvoiceWorkOrder, on_delete=models.CASCADE, verbose_name='发货单', help_text='发货单')
    cost = models.FloatField(default=0, verbose_name='服务金额', help_text='服务金额')
    quantity = models.IntegerField(default=0, verbose_name='货品总数', help_text='货品总数')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')


    class Meta:
        verbose_name = 'WOP-用户体验工单-服务单-发货单-验证'
        verbose_name_plural = verbose_name
        db_table = 'wop_satisfaction_service_invoice_check'

    def __str__(self):
        return str(self.id)










