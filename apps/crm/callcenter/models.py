from django.db import models
from apps.auth.users.models import UserProfile
from apps.base.shop.models import Shop
from apps.crm.customers.models import Customer
# Create your models here.



class OriCallLog(models.Model):

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '待核实'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
        (5, '特殊订单'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复建单'),
        (2, '无补寄原因'),
        (3, '无店铺'),
        (4, '补寄配件记录格式错误'),
        (5, '补寄原因错误'),
        (6, '单据创建失败'),
    )

    call_id = models.CharField(max_length=60, db_index=True, verbose_name='通话ID', help_text='通话ID')
    category = models.CharField(max_length=60, verbose_name='类型', help_text='类型')
    start_time = models.CharField(max_length=60, verbose_name='开启服务时间', help_text='开启服务时间')
    end_time = models.CharField(max_length=60, verbose_name='结束服务时间', help_text='结束服务时间')
    total_duration = models.CharField(max_length=60, verbose_name='服务时长', help_text='服务时长')
    call_duration = models.CharField(max_length=60, verbose_name='通话时长', help_text='通话时长')
    queue_time = models.CharField(max_length=60, verbose_name='排队时长', help_text='排队时长')
    ring_time = models.CharField(max_length=60, verbose_name='振铃时长', help_text='振铃时长')
    muted_duration = models.CharField(max_length=60, verbose_name='静音时长', help_text='静音时长')
    muted_time = models.CharField(max_length=60, verbose_name='静音次数', help_text='静音次数')
    calling_num = models.CharField(max_length=60, db_index=True, verbose_name='主叫号码', help_text='主叫号码')
    called_num = models.CharField(max_length=60, verbose_name='被叫号码', help_text='被叫号码')
    attribution = models.CharField(max_length=60, verbose_name='号码归属地', help_text='号码归属地')
    nickname = models.CharField(max_length=60, verbose_name='用户名', help_text='用户名')
    smartphone = models.CharField(max_length=60, verbose_name='手机号码', help_text='手机号码')
    ivr = models.CharField(max_length=60, verbose_name='ivr语音导航', help_text='ivr语音导航')
    group = models.CharField(max_length=60, verbose_name='分流客服组', help_text='分流客服组')
    servicer = models.CharField(max_length=60, verbose_name='接待客服', help_text='接待客服')
    repeated_num = models.CharField(max_length=60, verbose_name='重复咨询', help_text='重复咨询')
    answer_status = models.CharField(max_length=60, verbose_name='接听状态', help_text='接听状态')
    on_hook = models.CharField(max_length=60, verbose_name='挂机方', help_text='挂机方')
    satisfaction = models.CharField(max_length=60, verbose_name='满意度', help_text='满意度')
    call_recording = models.CharField(max_length=200, verbose_name='服务录音', help_text='服务录音')
    primary_classification = models.CharField(max_length=60, verbose_name='一级分类', help_text='一级分类')
    secondary_classification = models.CharField(max_length=60, verbose_name='二级分类', help_text='二级分类')
    three_level_classification = models.CharField(max_length=60, verbose_name='三级分类', help_text='三级分类')
    four_level_classification = models.CharField(max_length=60, verbose_name='四级分类', help_text='四级分类')
    five_level_classification = models.CharField(max_length=60, verbose_name='五级分类', help_text='五级分类')
    remark = models.CharField(max_length=200, verbose_name='咨询备注', help_text='咨询备注')
    problem_status = models.CharField(max_length=60, verbose_name='问题解决状态', help_text='问题解决状态')
    purchase_time = models.CharField(max_length=60, verbose_name='购买日期', help_text='购买日期')
    shop = models.CharField(max_length=60, verbose_name='购买店铺', help_text='购买店铺')
    goods_type = models.CharField(max_length=60, verbose_name='产品型号', help_text='产品型号')
    m_sn = models.CharField(max_length=60, verbose_name='出厂序列号', help_text='出厂序列号')
    is_order = models.CharField(max_length=60, db_index=True, verbose_name='是否建配件工单', help_text='是否建配件工单')
    order_category = models.CharField(max_length=60, verbose_name='补寄原因', help_text='补寄原因')
    goods_details = models.CharField(max_length=200, verbose_name='配件信息', help_text='配件信息')
    broken_part = models.CharField(max_length=50, verbose_name='损坏部位', help_text='损坏部位')
    description = models.CharField(max_length=200, verbose_name='损坏描述', help_text='损坏描述')
    receiver = models.CharField(max_length=60, verbose_name='收件人姓名', help_text='收件人姓名')
    mobile = models.CharField(max_length=60, verbose_name='建单手机', help_text='建单手机')
    area = models.CharField(max_length=60, verbose_name='省市区', help_text='省市区')
    address = models.CharField(max_length=60, verbose_name='详细地址', help_text='详细地址')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态')
    process_tag = models.IntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')
    class Meta:
        verbose_name = 'CRM-原始通话记录'
        verbose_name_plural = verbose_name
        db_table = 'crm_call_calllog_ori'

    def __str__(self):
        return self.calling_num

    @classmethod
    def verify_mandatory(cls, columns_key):
        VERIFY_FIELD = ["call_id", "category", "start_time", "end_time", "total_duration", "call_duration",
                        "queue_time", "ring_time", "muted_duration", "muted_time", "calling_num", "called_num",
                        "attribution", "nickname", "smartphone", "ivr", "group", "servicer", "repeated_num",
                        "answer_status", "on_hook", "satisfaction", "call_recording", "primary_classification",
                        "secondary_classification", "three_level_classification", "four_level_classification",
                        "five_level_classification", "remark", "problem_status", "purchase_time", "shop",
                        "goods_type", "m_sn", "is_order", "order_category", "goods_details", "broken_part",
                        "description", "receiver", "mobile", "area", "address"]

        for i in VERIFY_FIELD:
            if i not in columns_key:
                return 'verify_field error, must have mandatory field: "{}""'.format(i)
        else:
            return None


class CallLog(models.Model):

    ORDERSTATUS = (
        (0, '已取消'),
        (1, '未处理'),
        (2, '已完成'),
    )
    PROCESS_TAG = (
        (0, '未处理'),
        (1, '待核实'),
        (2, '已确认'),
        (3, '待清账'),
        (4, '已处理'),
        (5, '特殊订单'),
    )
    MISTAKE_LIST = (
        (0, '正常'),
        (1, '重复建单'),
        (2, '无补寄原因'),
        (3, '无店铺'),
        (4, '补寄配件记录格式错误'),
        (5, '补寄原因错误'),
        (6, '单据创建失败'),
    )

    call_id = models.CharField(max_length=60, db_index=True, verbose_name='通话ID', help_text='通话ID')
    category = models.CharField(max_length=60, verbose_name='类型', help_text='类型')
    start_time = models.CharField(max_length=60, verbose_name='开启服务时间', help_text='开启服务时间')
    end_time = models.CharField(max_length=60, verbose_name='结束服务时间', help_text='结束服务时间')
    total_duration = models.CharField(max_length=60, verbose_name='服务时长', help_text='服务时长')
    call_duration = models.CharField(max_length=60, verbose_name='通话时长', help_text='通话时长')
    queue_time = models.CharField(max_length=60, verbose_name='排队时长', help_text='排队时长')
    ring_time = models.CharField(max_length=60, verbose_name='振铃时长', help_text='振铃时长')
    muted_duration = models.CharField(max_length=60, verbose_name='静音时长', help_text='静音时长')
    muted_time = models.CharField(max_length=60, verbose_name='静音次数', help_text='静音次数')
    calling_num = models.CharField(max_length=60, verbose_name='主叫号码', help_text='主叫号码')
    called_num = models.CharField(max_length=60, verbose_name='被叫号码', help_text='被叫号码')
    attribution = models.CharField(max_length=60, verbose_name='号码归属地', help_text='号码归属地')
    nickname = models.CharField(max_length=60, verbose_name='用户名', help_text='用户名')
    smartphone = models.CharField(max_length=60, verbose_name='手机号码', help_text='手机号码')
    ivr = models.CharField(max_length=60, verbose_name='ivr语音导航', help_text='ivr语音导航')
    group = models.CharField(max_length=60, verbose_name='分流客服组', help_text='分流客服组')
    repeated_num = models.CharField(max_length=60, verbose_name='重复咨询', help_text='重复咨询')
    answer_status = models.CharField(max_length=60, verbose_name='接听状态', help_text='接听状态')
    on_hook = models.CharField(max_length=60, verbose_name='挂机方', help_text='挂机方')
    satisfaction = models.CharField(max_length=60, verbose_name='满意度', help_text='满意度')
    call_recording = models.CharField(max_length=200, verbose_name='服务录音', help_text='服务录音')
    primary_classification = models.CharField(max_length=60, verbose_name='一级分类', help_text='一级分类')
    secondary_classification = models.CharField(max_length=60, verbose_name='二级分类', help_text='二级分类')
    three_level_classification = models.CharField(max_length=60, verbose_name='三级分类', help_text='三级分类')
    four_level_classification = models.CharField(max_length=60, verbose_name='四级分类', help_text='四级分类')
    five_level_classification = models.CharField(max_length=60, verbose_name='五级分类', help_text='五级分类')
    remark = models.CharField(max_length=200, verbose_name='咨询备注', help_text='咨询备注')
    problem_status = models.CharField(max_length=60, verbose_name='问题解决状态', help_text='问题解决状态')
    purchase_time = models.CharField(max_length=60, verbose_name='购买日期', help_text='购买日期')
    goods_type = models.CharField(max_length=60, verbose_name='产品型号', help_text='产品型号')
    m_sn = models.CharField(max_length=60, verbose_name='出厂序列号', help_text='出厂序列号')
    is_order = models.CharField(max_length=60, verbose_name='是否建配件工单', help_text='是否建配件工单')
    order_category = models.CharField(max_length=60, verbose_name='补寄原因', help_text='补寄原因')
    goods_details = models.CharField(max_length=200, verbose_name='配件信息', help_text='配件信息')
    broken_part = models.CharField(max_length=50, verbose_name='损坏部位', help_text='损坏部位')
    description = models.CharField(max_length=200, verbose_name='损坏描述', help_text='损坏描述')
    receiver = models.CharField(max_length=60, verbose_name='收件人姓名', help_text='收件人姓名')
    mobile = models.CharField(max_length=60, verbose_name='建单手机', help_text='建单手机')
    area = models.CharField(max_length=60, verbose_name='省市区', help_text='省市区')
    address = models.CharField(max_length=60, verbose_name='详细地址', help_text='详细地址')

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, verbose_name='购买店铺', help_text='购买店铺')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='关联客户', help_text='关联客户' )
    servicer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='接待客服', help_text='接待客服')

    order_status = models.IntegerField(choices=ORDERSTATUS, default=1, db_index=True, verbose_name='单据状态')
    process_tag = models.IntegerField(choices=PROCESS_TAG, default=0, verbose_name='处理标签')
    mistake_tag = models.SmallIntegerField(choices=MISTAKE_LIST, default=0, verbose_name='错误列表')

    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'CRM-通话记录'
        verbose_name_plural = verbose_name
        db_table = 'crm_call_calllog'

    def __str__(self):
        return self.calling_num






