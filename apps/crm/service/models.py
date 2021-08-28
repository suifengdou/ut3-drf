from django.db import models

# Create your models here.
from django.db import models
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.utils.geography.models import Province, City, District
from apps.crm.customers.models import Customer


class OriMaintenance(models.Model):
    ERP_FIELD = {
        '保修单号': 'maintenance_order_id',
        '保修单状态': 'order_status',
        '收发仓库': 'warehouse',
        '是否已处理过': 'null',
        '处理登记人': 'completer',
        '保修类型': 'maintenance_type',
        '故障类型': 'fault_type',
        '送修类型': 'transport_type',
        '序列号': 'machine_sn',
        '换新序列号': 'new_machine_sn',
        '发货订单编号': 'send_order_id',
        '保修结束语': 'appraisal',
        '关联订单号': 'null',
        '关联店铺': 'shop',
        '购买时间': 'purchase_time',
        '创建时间': 'ori_create_time',
        '创建人': 'ori_creator',
        '审核时间': 'handle_time',
        '审核人': 'handler_name',
        '保修完成时间': 'finish_time',
        '保修金额': 'fee',
        '保修数量': 'quantity',
        '完成人': 'null',
        '最后修改时间': 'last_handle_time',
        '外部推送编号': 'null',
        '推送错误信息': 'null',
        '客户网名': 'buyer_nick',
        '寄件客户姓名': 'sender_name',
        '寄件客户固话': 'null',
        '寄件客户手机': 'sender_mobile',
        '寄件客户邮编': 'null',
        '寄件客户省市县': 'sender_area',
        '寄件客户地址': 'sender_address',
        '收件物流公司': 'send_logistics_company',
        '收件物流单号': 'send_logistics_no',
        '收件备注': 'send_memory',
        '寄回客户姓名': 'return_name',
        '寄回客户固话': 'null',
        '寄回客户手机': 'return_mobile',
        '寄回邮编': 'null',
        '寄回省市区': 'return_area',
        '寄回地址': 'return_address',
        '寄件指定物流公司': 'return_logistics_company',
        '寄件物流单号': 'return_logistics_no',
        '寄件备注': 'return_memory',
        '保修货品商家编码': 'goods_id',
        '保修货品名称': 'goods_name',
        '保修货品简称': 'goods_abbreviation',
        '故障描述': 'description',
        '是否在保修期内': 'is_guarantee'
    }

    VERIFY_FIELD = ["order_id", "order_status", "warehouse", "completer", "maintenance_type",
                    "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                    "appraisal", "shop", "purchase_time", "ori_create_time", "ori_creator", "handle_time",
                    "handler_name", "finish_time", "fee", "quantity", "last_handle_time", "buyer_nick",
                    "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                    "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                    "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                    "goods_id", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                    "charge_status", "charge_amount", "charge_memory"]

    ODER_STATUS = (
        (0, '未审核'),
        (1, '已处理'),
        (2, '无效'),
        (3, '异常'),
    )

    REPEAT_TAG_STATUS = (
        (0, '正常'),
        (1, '未处理'),
        (2, '产品'),
        (3, '维修'),
        (4, '其他'),
    )

    order_id = models.CharField(max_length=50, unique=True, verbose_name='保修单号')
    order_status = models.CharField(max_length=30, verbose_name='保修单状态')
    warehouse = models.CharField(max_length=50, verbose_name='收发仓库')
    completer = models.CharField(max_length=50, verbose_name='处理登记人')
    maintenance_type = models.CharField(max_length=50, verbose_name='保修类型')
    fault_type = models.CharField(max_length=50, verbose_name='故障类型')
    transport_type = models.CharField(max_length=50, verbose_name='送修类型')
    machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='序列号')
    new_machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='换新序列号')
    send_order_id = models.CharField(max_length=50, verbose_name='发货订单编号')
    appraisal = models.CharField(max_length=200, verbose_name='保修结束语')
    shop = models.CharField(max_length=60, verbose_name='关联店铺')
    purchase_time = models.DateTimeField(null=True, blank=True, verbose_name='购买时间')
    ori_create_time = models.DateTimeField(null=True, blank=True, verbose_name='创建时间')
    ori_creator = models.CharField(null=True, blank=True, max_length=50, verbose_name='创建人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    handler_name = models.CharField(max_length=50, verbose_name='审核人')
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name='保修完成时间')
    fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='保修金额')
    quantity = models.IntegerField(verbose_name='保修数量')
    last_handle_time = models.DateTimeField(null=True, blank=True, verbose_name='最后修改时间')
    buyer_nick = models.CharField(max_length=200, verbose_name='客户网名')
    sender_name = models.CharField(max_length=100, verbose_name='寄件客户姓名')
    sender_mobile = models.CharField(max_length=50, verbose_name='寄件客户手机')
    sender_area = models.CharField(max_length=50, verbose_name='寄件客户省市县')
    sender_address = models.CharField(max_length=200, verbose_name='寄件客户地址')
    send_logistics_company = models.CharField(max_length=50, verbose_name='收件物流公司')
    send_logistics_no = models.CharField(max_length=50, verbose_name='收件物流单号')
    send_memory = models.CharField(max_length=200, verbose_name='收件备注')
    return_name = models.CharField(max_length=50, verbose_name='寄回客户姓名')
    return_mobile = models.CharField(max_length=50, verbose_name='寄回客户手机')
    return_area = models.CharField(max_length=50, verbose_name='寄回省市区')
    return_address = models.CharField(max_length=200, verbose_name='寄回地址')
    return_logistics_company = models.CharField(max_length=50, verbose_name='寄件指定物流公司')
    return_logistics_no = models.CharField(max_length=50, verbose_name='寄件物流单号')
    return_memory = models.CharField(max_length=200, verbose_name='寄件备注')
    goods_id = models.CharField(max_length=60, verbose_name='保修货品商家编码')
    goods_name = models.CharField(max_length=150, verbose_name='保修货品名称')
    goods_abbreviation = models.CharField(max_length=60, verbose_name='保修货品简称')
    description = models.CharField(max_length=500, verbose_name='故障描述')
    is_guarantee = models.CharField(max_length=50, verbose_name='是否在保修期内')
    charge_status = models.CharField(default='', max_length=30, verbose_name='收费状态')
    charge_amount = models.IntegerField(default=0, verbose_name='收费金额')
    charge_memory = models.TextField(default='', verbose_name='收费说明')
    process_tag = models.SmallIntegerField(choices=ODER_STATUS, verbose_name='处理标签', default=0)
    towork_status = models.SmallIntegerField(choices=ODER_STATUS, verbose_name='递交状态', default=0)

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-原始保修单'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_ori'

    def __str__(self):
        return self.order_id

    @classmethod
    def verify_mandatory(cls, columns_key):
        for i in cls.VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class Maintenance(models.Model):

    ODER_STATUS = (
        (0, '已取消'),
        (1, '未计算'),
        (2, '未处理'),
        (3, '已完成'),
    )

    REPEAT_TAG_STATUS = (
        (0, '正常'),
        (1, '未处理'),
        (2, '产品'),
        (3, '维修'),
        (4, '其他'),
    )

    maintenance = models.ForeignKey(OriMaintenance, on_delete=models.CASCADE, verbose_name='原始保修单', help_text='原始保修单')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省', help_text='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='市', help_text='市')
    district = models.ForeignKey(District, on_delete=models.CASCADE, verbose_name='区', help_text='区')
    goods_name = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='客户', help_text='客户')

    order_id = models.CharField(unique=True, max_length=50, verbose_name='保修单号')
    warehouse = models.CharField(max_length=50, verbose_name='收发仓库')
    completer = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理登记人')
    maintenance_type = models.CharField(max_length=50, verbose_name='保修类型')
    fault_type = models.CharField(max_length=50, verbose_name='故障类型')
    machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='序列号')
    appraisal = models.CharField(max_length=200, verbose_name='保修结束语')
    description = models.CharField(max_length=500, verbose_name='故障描述')

    ori_create_time = models.DateTimeField(null=True, blank=True, verbose_name='创建时间')
    finish_time = models.DateTimeField(verbose_name='保修完成时间')
    buyer_nick = models.CharField(max_length=200, verbose_name='客户网名')
    sender_name = models.CharField(max_length=100, verbose_name='寄件客户姓名')
    sender_mobile = models.CharField(max_length=50, verbose_name='寄件客户手机')
    sender_area = models.CharField(max_length=50, verbose_name='寄件客户省市县')

    is_guarantee = models.CharField(max_length=50, verbose_name='是否在保')
    finish_date = models.DateTimeField(verbose_name='保修完成日期')
    finish_month = models.CharField(max_length=50, verbose_name='保修完成月度')
    finish_year = models.CharField(max_length=50, verbose_name='保修完成年度')

    repeat_tag = models.SmallIntegerField(choices=REPEAT_TAG_STATUS, verbose_name='重复维修标记', default=0)
    goods_type = models.CharField(null=True, max_length=60, verbose_name='保修货品型号')
    order_status = models.SmallIntegerField(default=0, choices=ODER_STATUS, verbose_name='单据状态')


    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-M-保修单明细'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance'

    def __str__(self):
        return self.order_id


class MaintenanceSummary(models.Model):
    finish_time = models.DateTimeField(verbose_name='保修完成日期')
    order_count = models.IntegerField(default=0, verbose_name='完成保修数量')
    repeat_found = models.IntegerField(default=0, verbose_name='当天发现30天二次维修量')
    repeat_today = models.IntegerField(default=0, verbose_name='当天二次维修量')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-M-保修统计表'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_summary'

    def __str__(self):
        return str(self.finish_time)

