from django.db import models

# Create your models here.
from django.db import models
from apps.base.shop.models import Shop
from apps.base.goods.models import Goods
from apps.utils.geography.models import Province, City, District
from apps.crm.customers.models import Customer
from apps.auth.users.models import UserProfile


class OriMaintenance(models.Model):

    VERIFY_FIELD = ["order_id", "ori_order_status", "warehouse", "completer", "maintenance_type",
                    "fault_type", "transport_type", "machine_sn", "new_machine_sn", "send_order_id",
                    "appraisal", "shop", "purchase_time", "ori_create_time", "ori_creator", "handle_time",
                    "handler_name", "finish_time", "fee", "quantity", "last_handle_time", "buyer_nick",
                    "sender_name", "sender_mobile", "sender_area", "sender_address", "send_logistics_company",
                    "send_logistics_no", "send_memory", "return_name", "return_mobile", "return_area",
                    "return_address", "return_logistics_company", "return_logistics_no", "return_memory",
                    "goods_id", "goods_name", "goods_abbreviation", "description", "is_guarantee",
                    "charge_status", "charge_amount", "charge_memory"]

    ODER_STATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已递交'),
        (3, '无效单'),
    )

    PROCESS_LIST = (
        (0, '无异常'),
        (1, '审核异常'),
        (2, '逆向异常'),
        (3, '取件异常'),
        (4, '入库异常'),
        (5, '维修异常'),
        (6, '超期异常'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '尝试修复数据'),
        (2, '二级市错误'),
        (3, '寄件地区出错'),
        (4, 'UT无此店铺'),
        (5, 'UT此型号整机未创建'),
        (6, 'UT系统无此店铺'),
        (7, '递交到保修单错乱'),
    )
    SIGN_LIST = (
        (0, '无'),
        (1, '等待核实'),
        (2, '专项处理'),
        (3, '暂不处理'),
        (4, '特殊问题'),
        (5, '上报待批'),
    )

    order_id = models.CharField(max_length=50, db_index=True, unique=True, verbose_name='保修单号', help_text='保修单号')
    ori_order_status = models.CharField(max_length=30, db_index=True, verbose_name='保修单状态', help_text='保修单状态')
    warehouse = models.CharField(max_length=50, verbose_name='收发仓库', help_text='收发仓库')
    completer = models.CharField(max_length=50, verbose_name='处理登记人', help_text='处理登记人')
    maintenance_type = models.CharField(max_length=50, verbose_name='保修类型', help_text='保修类型')
    fault_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='故障类型', help_text='故障类型')
    transport_type = models.CharField(max_length=50, verbose_name='送修类型', help_text='送修类型')
    machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='序列号', help_text='序列号')
    new_machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='换新序列号', help_text='换新序列号')
    send_order_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='发货订单编号', help_text='发货订单编号')
    appraisal = models.CharField(max_length=200, null=True, blank=True, verbose_name='保修结束语', help_text='保修结束语')
    shop = models.CharField(max_length=60, verbose_name='关联店铺', help_text='关联店铺')
    purchase_time = models.DateTimeField(null=True, blank=True, verbose_name='购买时间', help_text='购买时间')
    ori_created_time = models.DateTimeField(null=True, blank=True, verbose_name='创建时间', help_text='创建时间')
    ori_creator = models.CharField(null=True, blank=True, max_length=50, verbose_name='创建人', help_text='创建人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间', help_text='审核时间')
    handler = models.CharField(null=True, blank=True, max_length=50, verbose_name='审核人', help_text='审核人')
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name='保修完成时间', help_text='保修完成时间')
    fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='保修金额', help_text='保修金额')
    quantity = models.IntegerField(verbose_name='保修数量', help_text='保修数量')
    last_handle_time = models.DateTimeField(null=True, blank=True, verbose_name='最后修改时间', help_text='最后修改时间')
    buyer_nick = models.CharField(max_length=200, null=True, blank=True,verbose_name='客户网名', help_text='客户网名')
    sender_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='寄件客户姓名', help_text='寄件客户姓名')
    sender_mobile = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件客户手机', help_text='寄件客户手机')
    sender_area = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件客户省市县', help_text='寄件客户省市县')
    sender_address = models.CharField(max_length=200, null=True, blank=True, verbose_name='寄件客户地址', help_text='寄件客户地址')
    send_logistics_company = models.CharField(max_length=50, null=True, blank=True, verbose_name='收件物流公司', help_text='收件物流公司')
    send_logistics_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='收件物流单号', help_text='收件物流单号')
    send_memory = models.CharField(max_length=200, null=True, blank=True, verbose_name='收件备注', help_text='收件备注')
    return_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄回客户姓名', help_text='寄回客户姓名')
    return_mobile = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄回客户手机', help_text='寄回客户手机')
    return_area = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄回省市区', help_text='寄回省市区')
    return_address = models.CharField(max_length=200, null=True, blank=True, verbose_name='寄回地址', help_text='寄回地址')
    return_logistics_company = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件指定物流公司', help_text='寄件指定物流公司')
    return_logistics_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件物流单号', help_text='寄件物流单号')
    return_memory = models.CharField(max_length=200, null=True, blank=True, verbose_name='寄件备注', help_text='寄件备注')
    goods_id = models.CharField(max_length=60, verbose_name='保修货品商家编码', help_text='保修货品商家编码')
    goods_name = models.CharField(max_length=150, verbose_name='保修货品名称', help_text='保修货品名称')
    goods_abbreviation = models.CharField(max_length=60, verbose_name='保修货品简称', help_text='保修货品简称')
    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='故障描述', help_text='故障描述')
    is_guarantee = models.CharField(max_length=50, null=True, blank=True, verbose_name='是否在保修期内', help_text='是否在保修期内')
    charge_status = models.CharField(null=True, blank=True, max_length=30, verbose_name='收费状态', help_text='收费状态')
    charge_amount = models.FloatField(default=0, verbose_name='收费金额', help_text='收费金额')
    charge_memory = models.TextField(default='', null=True, blank=True,   verbose_name='收费说明', help_text='收费说明')

    suggestion = models.TextField(null=True, blank=True, max_length=250, verbose_name='处理意见', help_text='处理意见')
    cause = models.TextField(null=True, blank=True, max_length=250, verbose_name='异常原因', help_text='异常原因')
    process_tag = models.SmallIntegerField(choices=PROCESS_LIST, default=0, db_index=True, verbose_name='处理标签',
                                           help_text='处理标签')
    order_status = models.SmallIntegerField(choices=ODER_STATUS, default=1, db_index=True, verbose_name='递交状态',
                                            help_text='递交状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, db_index=True, verbose_name='错误标签',
                                           help_text='错误标签')
    sign = models.SmallIntegerField(choices=SIGN_LIST, default=0, db_index=True, verbose_name="标记名称", help_text="标记名称")
    warning_time = models.DateTimeField(null=True, blank=True,  verbose_name='节点时间', help_text='节点时间')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, db_index=True, max_length=150, verbose_name='创建者', help_text='创建者')

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


class OriMaintenanceGoods(models.Model):

    VERIFY_FIELD = ["order_id", "part_id", "part__name", "quantity", "part_memo", "handling_status",
                    "handling_content", "warehouse", "completer", "maintenance_type", "fault_type",
                    "transport_type", "goods_id", "goods_name", "machine_sn", "send_order_id", "appraisal",
                    "shop", "purchase_time", "ori_created_time", "ori_creator", "handle_time", "handler",
                    "finish_time", "last_handle_time", "sender_name", "sender_mobile", "sender_area",
                    "sender_address", "return_memory", "description", "is_guarantee"]

    ODER_STATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已递交'),
    )

    PROCESS_LIST = (
        (0, '未处理'),
        (1, '已处理'),
        (9, '特殊订单'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '尝试修复数据'),
    )

    order_id = models.CharField(max_length=50, db_index=True, unique=True, verbose_name='保修单号', help_text='保修单号')
    part_id = models.CharField(max_length=60, verbose_name='配件编码', help_text='保修货品商家编码')
    part_name = models.CharField(max_length=150, verbose_name='配件名称', help_text='保修货品名称')
    quantity = models.IntegerField(verbose_name='配件数量', help_text='配件数量')
    part_memo = models.CharField(max_length=200, null=True, blank=True, verbose_name='配件备注', help_text='配件备注')
    handling_status = models.CharField(max_length=30, db_index=True, verbose_name='处理状态', help_text='处理状态')
    handling_content = models.CharField(max_length=150, verbose_name='保修处理内容', help_text='保修处理内容')
    warehouse = models.CharField(max_length=50, verbose_name='收发仓库', help_text='收发仓库')
    completer = models.CharField(max_length=50, verbose_name='处理登记人', help_text='处理登记人')
    maintenance_type = models.CharField(max_length=50, verbose_name='保修类型', help_text='保修类型')
    fault_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='故障类型', help_text='故障类型')
    transport_type = models.CharField(max_length=50, verbose_name='送修类型', help_text='送修类型')
    goods_id = models.CharField(max_length=60, verbose_name='保修货品商家编码', help_text='保修货品商家编码')
    goods_name = models.CharField(max_length=150, verbose_name='保修货品名称', help_text='保修货品名称')

    machine_sn = models.CharField(null=True, blank=True, max_length=50, verbose_name='序列号', help_text='序列号')
    send_order_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='发货订单编号', help_text='发货订单编号')
    appraisal = models.CharField(max_length=200, null=True, blank=True, verbose_name='保修结束语', help_text='保修结束语')
    shop = models.CharField(max_length=60, verbose_name='关联店铺', help_text='关联店铺')
    purchase_time = models.DateTimeField(null=True, blank=True, verbose_name='购买时间', help_text='购买时间')
    ori_created_time = models.DateTimeField(null=True, blank=True, verbose_name='创建时间', help_text='创建时间')
    ori_creator = models.CharField(null=True, blank=True, max_length=50, verbose_name='创建人', help_text='创建人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间', help_text='审核时间')
    handler = models.CharField(null=True, blank=True, max_length=50, verbose_name='审核人', help_text='审核人')
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name='保修完成时间', help_text='保修完成时间')

    last_handle_time = models.DateTimeField(null=True, blank=True, verbose_name='最后修改时间', help_text='最后修改时间')
    sender_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='寄件客户姓名', help_text='寄件客户姓名')
    sender_mobile = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件客户手机', help_text='寄件客户手机')
    sender_area = models.CharField(max_length=50, null=True, blank=True, verbose_name='寄件客户省市县', help_text='寄件客户省市县')
    sender_address = models.CharField(max_length=200, null=True, blank=True, verbose_name='寄件客户地址', help_text='寄件客户地址')
    return_memory = models.CharField(max_length=200, null=True, blank=True, verbose_name='寄件备注', help_text='寄件备注')

    description = models.CharField(max_length=500, null=True, blank=True, verbose_name='故障描述', help_text='故障描述')
    is_guarantee = models.CharField(max_length=50, null=True, blank=True, verbose_name='是否在保修期内', help_text='是否在保修期内')

    suggestion = models.TextField(null=True, blank=True, max_length=250, verbose_name='处理意见', help_text='处理意见')
    process_tag = models.SmallIntegerField(choices=PROCESS_LIST, default=0, db_index=True, verbose_name='处理标签',
                                           help_text='处理标签')
    order_status = models.SmallIntegerField(choices=ODER_STATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, db_index=True, verbose_name='错误标签',
                                           help_text='错误标签')
    warning_time = models.DateTimeField(null=True, blank=True,  verbose_name='节点时间', help_text='节点时间')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, db_index=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-原始保修单-配件'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_ori_parts'

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
        (4, '客服'),
        (4, '快递'),
        (4, '用户'),
    )

    ori_order = models.ForeignKey(OriMaintenance, on_delete=models.CASCADE, verbose_name='原始保修单', help_text='原始保修单')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='店铺', help_text='店铺')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省', help_text='省')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='市', help_text='市')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='货品', help_text='货品')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True, verbose_name='客户', help_text='客户')

    order_id = models.CharField(unique=True, max_length=50, verbose_name='保修单号', help_text='保修单号')
    warehouse = models.CharField(max_length=50, verbose_name='收发仓库', help_text='收发仓库')
    maintenance_type = models.CharField(max_length=50, verbose_name='保修类型', help_text='保修类型')
    fault_type = models.CharField(max_length=50, verbose_name='故障类型', help_text='故障类型')
    machine_sn = models.CharField(null=True, blank=True, db_index=True, max_length=50, verbose_name='序列号', help_text='序列号')
    appraisal = models.CharField(max_length=200, verbose_name='保修结束语', help_text='保修结束语')
    description = models.CharField(max_length=500, verbose_name='故障描述', help_text='故障描述')

    buyer_nick = models.CharField(max_length=200, verbose_name='客户网名', help_text='客户网名')
    sender_name = models.CharField(max_length=100, verbose_name='寄件客户姓名', help_text='寄件客户姓名')
    sender_mobile = models.CharField(max_length=50, verbose_name='寄件客户手机', help_text='寄件客户手机')

    is_guarantee = models.CharField(max_length=50, verbose_name='是否在保', help_text='是否在保')
    charge_status = models.CharField(default='', max_length=30, verbose_name='收费状态', help_text='收费状态')
    charge_amount = models.IntegerField(default=0, verbose_name='收费金额', help_text='收费金额')
    charge_memory = models.TextField(default='', verbose_name='收费说明', help_text='收费说明')

    ori_creator = models.CharField(null=True, blank=True, max_length=50, verbose_name='创建人', help_text='创建人')
    ori_created_time = models.DateTimeField(null=True, blank=True, verbose_name='创建时间', help_text='创建时间')
    handler_name = models.CharField(max_length=50, verbose_name='审核人', help_text='审核人')
    handle_time = models.DateTimeField(null=True, blank=True, verbose_name='审核时间', help_text='审核时间')
    completer = models.CharField(null=True, blank=True, max_length=50, verbose_name='处理登记人', help_text='处理登记人')
    finish_time = models.DateTimeField(verbose_name='保修完成时间', help_text='保修完成时间')

    memo = models.CharField(null=True, blank=True, max_length=230, verbose_name='判责说明', help_text='判责说明')

    repeat_tag = models.SmallIntegerField(choices=REPEAT_TAG_STATUS, default=0, db_index=True, verbose_name='重复维修标记', help_text='重复维修标记')
    order_status = models.SmallIntegerField(default=1, choices=ODER_STATUS, db_index=True, verbose_name='单据状态', help_text='单据状态')
    found_tag = models.BooleanField(default=False, verbose_name="发现二次维修", help_text="发现二次维修")

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-M-保修单明细'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance'
        permissions = (
            # (权限，权限描述),
            ('view_user_maintenance', 'Can view user CRM-M-保修单明细-用户'),
            ('view_handler_maintenance', 'Can view handler CRM-M-保修单明细-处理'),
        )

    def __str__(self):
        return self.order_id


class MaintenanceGoods(models.Model):

    ODER_STATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已递交'),
    )

    PROCESS_LIST = (
        (0, '未处理'),
        (1, '已处理'),
        (9, '特殊订单'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '尝试修复数据'),
    )
    order = models.ForeignKey(Maintenance, on_delete=models.CASCADE, verbose_name='保修单', help_text='保修单')
    part = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name="part", verbose_name='配件', help_text='配件')
    quantity = models.IntegerField(verbose_name='配件数量', help_text='配件数量')
    part_memo = models.CharField(max_length=200, null=True, blank=True, verbose_name='配件备注', help_text='配件备注')

    process_tag = models.SmallIntegerField(choices=PROCESS_LIST, default=0, db_index=True, verbose_name='处理标签',
                                           help_text='处理标签')
    order_status = models.SmallIntegerField(choices=ODER_STATUS, default=1, db_index=True, verbose_name='单据状态',
                                            help_text='单据状态')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, db_index=True, verbose_name='错误标签',
                                           help_text='错误标签')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, db_index=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-保修单-配件'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_parts'

    def __str__(self):
        return self.order_id


class FindAndFound(models.Model):
    find = models.OneToOneField(Maintenance, on_delete=models.CASCADE, related_name='m_find', verbose_name='发现二次',
                                help_text='发现二次')
    found = models.OneToOneField(Maintenance, on_delete=models.CASCADE, related_name='m_found', verbose_name='二次保修单',
                                 help_text='二次保修单')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-M-二次维修关系'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_ff'

    def __str__(self):
        return str(self.id)


class MaintenanceSummary(models.Model):
    finish_date = models.DateField(db_index=True, verbose_name='保修完成日期', help_text='保修完成日期')
    order_count = models.IntegerField(default=0, verbose_name='完成保修数量', help_text='完成保修数量')
    repeat_found = models.IntegerField(default=0, verbose_name='当天发现30天二次维修量', help_text='当天发现30天二次维修量')
    repeat_today = models.IntegerField(default=0, verbose_name='当天二次维修量', help_text='当天二次维修量')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-M-保修统计表'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_summary'

    def __str__(self):
        return str(self.finish_date)


class LogOriMaintenance(models.Model):
    obj = models.ForeignKey(OriMaintenance, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-原始保修单-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_ori_logging'

    def __str__(self):
        return str(self.id)


class LogOriMaintenanceGoods(models.Model):
    obj = models.ForeignKey(OriMaintenanceGoods, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-原始保修单-配件-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_ori_parts_logging'

    def __str__(self):
        return str(self.id)


class LogMaintenance(models.Model):
    obj = models.ForeignKey(Maintenance, on_delete=models.CASCADE, verbose_name='对象', help_text='对象')
    name = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='操作人', help_text='操作人')
    content = models.CharField(max_length=240, verbose_name='操作内容', help_text='操作内容')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')

    class Meta:
        verbose_name = 'CRM-M-保修单明细-日志'
        verbose_name_plural = verbose_name
        db_table = 'crm_maintenance_logging'

    def __str__(self):
        return str(self.id)






