from django.db import models
from apps.base.department.models import Department
from apps.base.company.models import Company
from apps.base.goods.models import Goods
from apps.base.shop.models import Shop
from apps.utils.geography.models import City, Province

class OriInvoice(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '申请未报'),
        (2, '正在审核'),
        (3, '单据生成'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '开票中'),
        (2, '已开票'),
        (3, '待买票'),
        (4, '信息错'),
        (5, '被驳回'),
        (6, '已处理'),
        (7, '未申请'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '没开票公司'),
        (2, '货品错误'),
        (3, '专票信息缺'),
        (4, '收件手机错'),
        (5, '超限额发票'),
        (6, '递交发票订单出错'),
        (7, '生成发票货品出错'),
        (8, '单货品超限额非法'),
        (9, '发票订单生成重复'),
        (10, '生成发票订单出错'),
        (11, '生成发票订单货品出错'),
        (12, '单据被驳回'),
        (13, '税号错误'),
        (14, '源单号格式错误'),
        (15, '导入货品错误'),
        (16, '源单号格式错误'),
    )

    LOGICAL_DECISION = (
        (0, '否'),
        (1, '是'),
    )
    CATEGORY = (
        (1, '专票'),
        (2, '普票'),
    )

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='receipt_c', null=True, blank=True, verbose_name='收款开票公司', help_text='收款开票公司')
    order_id = models.CharField(unique=True, max_length=100, verbose_name='源单号', help_text='源单号')
    order_category = models.SmallIntegerField(choices=CATEGORY, verbose_name='发票类型', help_text='发票类型')

    title = models.CharField(max_length=150, verbose_name='发票抬头', help_text='发票抬头')
    tax_id = models.CharField(max_length=60, verbose_name='纳税人识别号', help_text='纳税人识别号')
    phone = models.CharField(null=True, blank=True, max_length=60, verbose_name='联系电话', help_text='联系电话')
    bank = models.CharField(null=True, blank=True, max_length=100, verbose_name='银行名称', help_text='银行名称')
    account = models.CharField(null=True, blank=True, max_length=60, verbose_name='银行账号', help_text='银行账号')
    address = models.CharField(null=True, blank=True, max_length=200, verbose_name='地址', help_text='地址')
    remark = models.CharField(null=True, blank=True, max_length=230, verbose_name='发票备注', help_text='发票备注')

    sent_consignee = models.CharField(max_length=150, verbose_name='收件人姓名', help_text='收件人姓名')
    sent_smartphone = models.CharField(max_length=30, verbose_name='收件人手机', help_text='收件人手机')
    sent_city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True, verbose_name='收件城市', help_text='收件城市')
    sent_district = models.CharField(null=True, blank=True, max_length=30, verbose_name='收件区县', help_text='收件区县')
    sent_address = models.CharField(max_length=200, verbose_name='收件地址', help_text='收件地址')

    amount = models.FloatField(default=0, verbose_name='申请税前开票总额', help_text='申请税前开票总额')

    is_deliver = models.BooleanField(default=False,  verbose_name='是否发顺丰', help_text='是否发顺丰')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='申请提交时间', help_text='申请提交时间')

    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='开票处理时间', help_text='开票处理时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='开票处理间隔(分钟)', help_text='开票处理间隔(分钟)')

    message = models.CharField(null=True, blank=True, max_length=300, verbose_name='工单留言', help_text='工单留言')
    memorandum = models.CharField(null=True, blank=True, max_length=300, verbose_name='工单反馈', help_text='工单反馈')

    sign_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sign_company', null=True, blank=True, verbose_name='创建公司', help_text='创建公司')
    sign_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sign_department', null=True, blank=True, verbose_name='创建部门', help_text='创建部门')

    nickname = models.CharField(max_length=150, null=True, blank=True, verbose_name='客户昵称', help_text='客户昵称')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, db_index=True, verbose_name='创建者', help_text='创建者')

    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, db_index=True, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, db_index=True, verbose_name='工单状态', help_text='工单状态')

    class Meta:
        verbose_name = 'WOP-发票工单-查询'
        verbose_name_plural = verbose_name
        db_table = 'wop_invoice_ori'

        permissions = (
            # (权限，权限描述),
            ('view_applicant_oriinvoice', 'Can view applicant WOP-发票工单-申请'),
            ('view_user_oriinvoice', 'Can view user WOP-发票工单-用户'),
            ('view_handler_oriinvoice', 'Can view handler WOP-发票工单-处理'),
        )

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['shop', 'company', 'order_id', 'order_category', 'title', 'tax_id', 'phone', 'bank', 'account',
                        'remark', 'sent_consignee', 'sent_smartphone', 'sent_address',
                        'is_deliver', 'message', 'goods_id', 'goods_name', 'quantity', 'price']

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class OriInvoiceGoods(models.Model):

    invoice = models.ForeignKey(OriInvoice, on_delete=models.CASCADE, verbose_name='发票工单', help_text='发票工单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True, help_text='货品编码')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称', help_text='货品名称')
    quantity = models.IntegerField(verbose_name='数量', help_text='数量')
    price = models.FloatField(verbose_name='含税单价', help_text='含税单价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')


    class Meta:
        verbose_name = 'WOP-发票工单-货品明细'
        verbose_name_plural = verbose_name
        unique_together = (('invoice', 'goods_name'))
        db_table = 'wop_invoice_ori_goods'

    def __str__(self):
        return self.invoice.order_id


class Invoice(models.Model):
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '开票处理'),
        (2, '终审复核'),
        (3, '工单完结'),
    )
    PROCESSTAG = (
        (0, '未处理'),
        (1, '开票中'),
        (2, '已开票'),
        (3, '待开票'),
        (4, '待打单'),
        (5, '已开票已打单'),
        (6, '已处理'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '无发票号或工单未开全'),
        (2, '快递单错误'),
        (3, '快递未发货'),
        (4, '驳回出错'),

    )

    LOGICAL_DEXISION = (
        (0, '否'),
        (1, '是'),
    )
    CATEGORY = (
        (1, '专票'),
        (2, '普票'),
    )

    work_order = models.ForeignKey(OriInvoice, on_delete=models.CASCADE, verbose_name='来源单号', help_text='来源单号')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='receipt_c_invoice', null=True, blank=True, verbose_name='收款开票公司', help_text='收款开票公司')
    order_id = models.CharField(unique=True, max_length=100, verbose_name='开票单号', help_text='开票单号')
    order_category = models.SmallIntegerField(choices=CATEGORY, verbose_name='发票类型', help_text='发票类型')
    invoice_id = models.CharField(null=True, blank=True, unique=True, max_length=60, verbose_name='发票号码', help_text='发票号码')

    title = models.CharField(max_length=150, verbose_name='发票抬头', help_text='发票抬头')
    tax_id = models.CharField(max_length=60, verbose_name='纳税人识别号', help_text='纳税人识别号')
    phone = models.CharField(null=True, blank=True, max_length=60, verbose_name='联系电话', help_text='联系电话')
    bank = models.CharField(null=True, blank=True, max_length=100, verbose_name='银行名称', help_text='银行名称')
    account = models.CharField(null=True, blank=True, max_length=60, verbose_name='银行账号', help_text='银行账号')
    address = models.CharField(null=True, blank=True, max_length=200, verbose_name='地址', help_text='地址')
    remark = models.CharField(null=True, blank=True, max_length=230, verbose_name='发票备注', help_text='发票备注')

    sent_consignee = models.CharField(max_length=150, verbose_name='收件人姓名', help_text='收件人姓名')
    sent_smartphone = models.CharField(max_length=30, verbose_name='收件人手机', help_text='收件人手机')
    sent_province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='收件省份', help_text='收件省份')
    sent_city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='收件城市', help_text='收件城市')
    sent_district = models.CharField(null=True, blank=True, max_length=30, verbose_name='收件区县', help_text='收件区县')
    sent_address = models.CharField(max_length=200, verbose_name='收件地址', help_text='收件地址')

    amount = models.FloatField(default=0, verbose_name='发票税前开票总额', help_text='发票税前开票总额')
    ori_amount = models.FloatField(verbose_name='源工单开票总额', help_text='源工单开票总额')

    is_deliver = models.SmallIntegerField(choices=LOGICAL_DEXISION, verbose_name='是否顺丰', help_text='是否顺丰')
    track_no = models.CharField(null=True, blank=True, max_length=160, verbose_name='快递信息', help_text='快递信息')

    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='申请提交时间', help_text='申请提交时间')

    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='开票处理时间', help_text='开票处理时间')
    handle_interval = models.IntegerField(null=True, blank=True, verbose_name='开票处理间隔(分钟)', help_text='开票处理间隔(分钟)')

    message = models.CharField(null=True, blank=True, max_length=300, verbose_name='工单留言', help_text='工单留言')
    memorandum = models.CharField(null=True, blank=True, max_length=300, verbose_name='工单反馈', help_text='工单反馈')

    sign_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inv_sign_company', null=True,
                                     blank=True, verbose_name='创建公司', help_text='创建公司')
    sign_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='inv_sign_department',
                                        null=True, blank=True, verbose_name='创建部门', help_text='创建部门')

    nickname = models.CharField(max_length=150, null=True, blank=True, verbose_name='客户昵称', help_text='客户昵称')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    process_tag = models.SmallIntegerField(choices=PROCESSTAG, default=0, verbose_name='处理标签', help_text='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, db_index=True, verbose_name='订单状态', help_text='订单状态')

    class Meta:
        verbose_name = 'WOP-发票订单-查询'
        verbose_name_plural = verbose_name
        db_table = 'wop_invoice'
        permissions = (
            # (权限，权限描述),
            ('view_handler_invoice', 'Can view handler WOP-发票订单-审核'),
        )


    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ['order_id', 'information', 'category']
        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class InvoiceGoods(models.Model):

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, verbose_name='发票订单', help_text='发票订单')
    goods_id = models.CharField(max_length=50, verbose_name='货品编码', db_index=True, help_text='货品编码')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品名称', help_text='货品名称')
    goods_nickname = models.CharField(max_length=100, null=True, blank=True, verbose_name='货品简称', help_text='货品简称')
    quantity = models.IntegerField(verbose_name='数量', help_text='数量')
    price = models.FloatField(verbose_name='含税单价', help_text='含税单价')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='备注', help_text='备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-发票订单-货品明细'
        verbose_name_plural = verbose_name
        db_table = 'wop_invoice_goods'

    def __str__(self):
        return self.invoice.order_id


class DeliverOrder(models.Model):
    VERIFY_FIELD = ['ori_order_id', 'logistics', 'track_no']
    ORDER_STATUS = (
        (0, '已被取消'),
        (1, '等待打单'),
        (2, '打印完成'),
    )
    PROCESS_TAG = (
        (0, '待打印'),
        (1, '已打印'),
        (2, '暂停发'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '未打印'),
        (2, '快递信息回写失败'),

    )

    work_order = models.ForeignKey(OriInvoice, on_delete=models.CASCADE, related_name='ori_invoice',
                                   verbose_name='来源单号', help_text='来源单号')
    shop = models.CharField(max_length=60, verbose_name='店铺名称', help_text='店铺名称')
    ori_order_id = models.CharField(max_length=250, verbose_name='原始单号', db_index=True, help_text='原始单号')
    nickname = models.CharField(max_length=200, verbose_name='网名', help_text='网名')
    consignee = models.CharField(max_length=200, verbose_name='收件人', help_text='收件人')
    address = models.CharField(max_length=300, verbose_name='地址', help_text='地址')
    smartphone = models.CharField(max_length=60, verbose_name='手机', help_text='手机')
    condition_deliver = models.CharField(max_length=30, default='款到发货', verbose_name='发货条件', help_text='发货条件')
    discounts = models.SmallIntegerField(default=0, verbose_name='优惠金额', help_text='优惠金额')
    postage = models.SmallIntegerField(default=0, verbose_name='邮费', help_text='邮费')
    receivable = models.SmallIntegerField(default=0, verbose_name='应收合计', help_text='应收合计')
    goods_price = models.SmallIntegerField(default=0, verbose_name='货品价格', help_text='货品价格')
    goods_amount = models.SmallIntegerField(default=0, verbose_name='货品总价', help_text='货品总价')
    goods_id = models.CharField(max_length=100, default='00000090', verbose_name='商家编码', help_text='商家编码')
    goods_name = models.CharField(max_length=100, default='文件：发票', verbose_name='货品名称', help_text='货品名称')
    quantity = models.SmallIntegerField(default=1, verbose_name='货品数量', help_text='货品数量')
    order_category = models.CharField(max_length=30, default='线下零售', verbose_name='订单类别', help_text='订单类别')
    message = models.CharField(max_length=150, verbose_name='客服备注', help_text='客服备注')
    remark = models.CharField(null=True, blank=True, max_length=150, verbose_name='买家备注', help_text='买家备注')
    province = models.CharField(max_length=60, verbose_name='省', help_text='省')
    city = models.CharField(max_length=60, verbose_name='市', help_text='市')
    district = models.CharField(null=True, blank=True, max_length=60, verbose_name='区', help_text='区')

    logistics = models.CharField(max_length=60, verbose_name='快递公司', help_text='快递公司')
    track_no = models.CharField(null=True, blank=True, max_length=60, verbose_name='快递单号', help_text='快递单号')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS, default=1, verbose_name='单据状态', help_text='单据状态')
    process_tag = models.SmallIntegerField(choices=PROCESS_TAG, default=0, verbose_name='单据状态', help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误原因', help_text='错误原因')
    memorandum = models.CharField(null=True, blank=True, max_length=200, verbose_name='单据备注', help_text='单据备注')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'WOP-发票快递单-查询'
        verbose_name_plural = verbose_name
        db_table = 'wop_invoice_deliver'

    def __str__(self):
        return self.work_order.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None