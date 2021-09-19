import pandas as pd
import numpy as np
import datetime
import re
from functools import reduce
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import OriInvoiceSerializer, OriInvoiceGoodsSerializer, InvoiceSerializer, InvoiceGoodsSerializer, \
    DeliverOrderSerializer
from .models import OriInvoice, OriInvoiceGoods, Invoice, InvoiceGoods, DeliverOrder
from .filters import OriInvoiceFilter, OriInvoiceGoodsFilter, InvoiceFilter, InvoiceGoodsFilter, DeliverOrderFilter
from ut3.permissions import Permissions
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.decorators import action

from apps.base.goods.models import Goods
from apps.base.company.models import Company
from apps.base.shop.models import Shop
from apps.utils.geography.models import City, District


class OriInvoiceApplicateViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始发票工单
    list:
        返回原始发票工单列表
    update:
        更新原始发票工单信息
    destroy:
        删除原始发票工单信息
    create:
        创建原始发票工单信息
    partial_update:
        更新部分原始发票工单字段
    """
    serializer_class = OriInvoiceSerializer
    filter_class = OriInvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_applicant_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriInvoice.objects.none()
        queryset = OriInvoice.objects.filter(order_status=1,
                                             creator__exact=self.request.user.username,
                                             process_tag__exact=7).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for work_order in check_list:
                check_fields = ['order_id', 'invoice_id', 'title', 'tax_id', 'phone', 'bank', 'account',
                                'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address']
                for key in check_fields:
                    value = getattr(work_order, key, None)
                    if value:
                        setattr(work_order, key, str(value).replace(' ', '').replace("'", '').replace('\n', ''))
                if not work_order.company:
                    data["error"].append("%s 没开票公司" % work_order.order_id)
                    work_order.mistake_tag = 1
                    work_order.save()
                    n -= 1
                    continue

                if work_order.amount <= 0:
                    data["error"].append("%s 没添加货品, 或者货品价格添加错误" % work_order.order_id)
                    work_order.mistake_tag = 2
                    work_order.save()
                    n -= 1
                    continue
                # 判断专票信息是否完整
                if work_order.order_category == 1:
                    if not any([work_order.phone, work_order.bank, work_order.account, work_order.address]):
                        data["error"].append("%s 专票信息缺" % work_order.order_id)
                        work_order.mistake_tag = 3
                        work_order.save()
                        n -= 1
                        continue
                if work_order.is_deliver == 1:
                    if not re.match(r'^[0-9-]+$', work_order.sent_smartphone):
                        data["error"].append("%s 收件人手机错误" % work_order.order_id)
                        work_order.mistake_tag = 4
                        work_order.save()
                        n -= 1
                        continue
                if not re.match(
                        "^([13598Y]{1})([12349]{1})([0-9ABCDEFGHJKLMNPQRTUWXY]{6})([0-9ABCDEFGHJKLMNPQRTUWXY]{9})([0-9ABCDEFGHJKLMNPQRTUWXY])$",
                        work_order.tax_id):
                    data["error"].append("%s 税号错误" % work_order.order_id)
                    work_order.mistake_tag = 13
                    work_order.save()
                    n -= 1
                    continue
                if not re.match(r"^[0-9A-Z,]+$", work_order.order_id):
                    data["error"].append("%s 源单号错误，只支持大写字母和数字以及英文逗号" % work_order.order_id)
                    work_order.mistake_tag = 16
                    work_order.save()
                    n -= 1
                    continue
                if not work_order.memorandum:
                    work_order.memorandum = ''
                work_order.mistake_tag = 0
                work_order.process_tag = 0
                work_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriInvoiceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriInvoice.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriInvoiceFilter(params)
        serializer = OriInvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        print(request)
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {
            '店铺': 'shop',
            '收款开票公司': 'company',
            '源单号': 'order_id',
            '发票类型': 'order_category',
            '发票抬头': 'title',
            '纳税人识别号': 'tax_id',
            '联系电话': 'phone',
            '银行名称': 'bank',
            '银行账号': 'account',
            '地址': 'address',
            '发票备注': 'remark',
            '收件人姓名': 'sent_consignee',
            '收件人手机': 'sent_smartphone',
            '收件城市': 'sent_city',
            '收件区县': 'sent_district',
            '收件地址': 'sent_address',
            '是否发顺丰': 'is_deliver',
            '工单留言': 'message',
            '货品编码': 'goods_id',
            '货品名称': 'goods_name',
            '数量': 'quantity',
            '含税单价': 'price',
            '用户昵称': 'nickname',
        }
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0, converters={u'货品编码': str})
                FILTER_FIELDS = ['店铺', '收款开票公司', '源单号', '发票类型', '发票抬头', '纳税人识别号', '联系电话', '银行名称',
                                 '银行账号', '地址', '发票备注', '收件人姓名', '收件人手机', '收件城市', '收件区县', '收件地址',
                                 '是否发顺丰', '工单留言', '货品编码', '货品名称', '数量', '含税单价', '用户昵称']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    columns_key[i] = columns_key[i].replace(' ', '').replace('=', '')

                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = OriInvoice.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic["error"].append(str(_ret_verify_field))
                    return report_dic

                # 更改一下DataFrame的表名称
                columns_key_ori = df.columns.values.tolist()
                ret_columns_key = dict(zip(columns_key_ori, columns_key))
                df.rename(columns=ret_columns_key, inplace=True)
                check_list = ['shop', 'company', 'order_id', 'order_category', 'title', 'tax_id', 'phone', 'bank',
                              'account', 'address', 'remark', 'sent_consignee', 'sent_smartphone',
                              'sent_city', 'sent_district', 'sent_address', 'is_deliver', 'goods_id']
                df_check = df[check_list]

                tax_ids = list(set(df_check.tax_id))
                for tax_id in tax_ids:
                    data_check = df_check[df_check.tax_id == tax_id]
                    check_list.pop()
                    if len(data_check.goods_id) != len(list(set(data_check.goods_id))):
                        error = '税号%s，货品重复，请剔除重复货品' % str(tax_id)
                        report_dic["error"].append(error)
                        return report_dic
                    for word in check_list:
                        check_word = data_check[word]
                        if np.any(check_word.isnull() == True):
                            continue
                        check_word = list(set(check_word))
                        if len(check_word) > 1:
                            error = '税号%s的%s不一致，相同税号%s必须相同' % (str(tax_id), str(word), str(word))
                            report_dic["error"].append(error)
                            return report_dic

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                for tax_id in tax_ids:
                    df_invoice = df[df.tax_id == tax_id]
                    _ret_list = df_invoice.to_dict(orient='records')
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        work_order = OriInvoice()

        if not re.match(r'^[0-9A-Z]+$', str(resource[0]['order_id'])):
            error = '源单号%s非法，请使用正确的源单号格式（只支持英文字母和数字组合）' % resource[0]['order_id']
            report_dic['error'].append(error)
            return report_dic
        else:
            work_order.order_id = resource[0]['order_id']

        _q_work_order = OriInvoice.objects.filter(order_id=str(resource[0]['order_id']))
        if not _q_work_order.exists():
            # 开始导入数据
            check_list = ['title', 'tax_id', 'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address',
                          'phone', 'bank', 'account', 'address', 'remark', 'message', 'nickname']

            _q_shop = Shop.objects.filter(name=resource[0]['shop'])
            if _q_shop.exists():
                work_order.shop = _q_shop[0]
            else:
                error = '店铺%s不存在，请使用正确的店铺名' % resource[0]['shop']
                report_dic['error'].append(error)
                return report_dic
            _q_company = Company.objects.filter(name=resource[0]['company'])
            if _q_company.exists():
                work_order.company = _q_company[0]
            else:
                error = '开票公司%s不存在，请使用正确的公司名' % resource[0]['company']
                report_dic['error'].append(error)
                return report_dic
            category = {
                '专票': 1,
                '普票': 2,
            }
            order_category = category.get(resource[0]['order_category'], None)
            if order_category:
                work_order.order_category = order_category

            else:
                error = '开票类型%s不存在，请使用正确的开票类型' % resource[0]['order_category']
                report_dic['error'].append(error)
                return report_dic

            _q_city = City.objects.filter(city=str(resource[0]['sent_city']))
            if _q_city.exists():
                work_order.sent_city = _q_city[0]
            else:
                error = '城市%s非法，请使用正确的二级城市名称' % resource[0]['sent_city']
                report_dic['error'].append(error)
                return report_dic

            logical_decision = {
                '是': 1,
                '否': 0,
            }
            is_deliver = logical_decision.get(resource[0]['is_deliver'], None)
            if is_deliver is None:
                error = '是否发顺丰字段：%s非法（只可以填是否）' % resource[0]['is_deliver']
                report_dic['error'].append(error)
                return report_dic
            else:
                work_order.is_deliver = is_deliver

            if order_category == 1:
                check_list = check_list[:10]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开专票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            elif order_category == 2:
                check_list = check_list[:6]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开普票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            if self.request.user.company:
                work_order.sign_company = self.request.user.company
            else:
                error = '账号公司未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            if self.request.user.department:
                work_order.sign_department = self.request.user.department
            else:
                error = '账号部门未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            for attr in check_list:
                if resource[0][attr]:
                    setattr(work_order, attr, resource[0][attr])

            try:
                work_order.creator = self.request.user.username
                work_order.process_tag = 7
                work_order.save()
                report_dic["successful"] += 1
            # 保存出错，直接错误条数计数加一。
            except Exception as e:
                report_dic["error"].append(e)
                report_dic["false"] += 1
                return report_dic
        else:
            work_order = _q_work_order[0]
            if work_order.order_status != 1:
                error = '此订单%s已经存在，请核实再导入' % (work_order.order_id)
                report_dic["error"].append(error)
                report_dic["false"] += 1
                return report_dic
            work_order.process_tag = 7
            work_order.save()
            all_goods_info = work_order.oriinvoicegoods_set.all()
            all_goods_info.delete()

        goods_ids = [row['goods_id'] for row in resource]
        goods_quantity = [row['quantity'] for row in resource]
        goods_prices = [row['price'] for row in resource]

        for goods_id, quantity, price in zip(goods_ids, goods_quantity, goods_prices):
            goods_order = OriInvoiceGoods()
            _q_goods_id = Goods.objects.filter(goods_id=goods_id)
            if _q_goods_id.exists():
                goods_order.goods_name = _q_goods_id[0]
                goods_order.goods_id = goods_id
                goods_order.quantity = quantity
                goods_order.price = price
                goods_order.invoice = work_order
                goods_order.creator = self.request.user.username
                try:
                    goods_order.save()
                    report_dic["successful"] += 1
                # 保存出错，直接错误条数计数加一。
                except Exception as e:
                    report_dic["error"].append(e)
                    report_dic["false"] += 1
                    work_order.mistake_tag = 15
                    work_order.save()
                    return report_dic
            else:
                error = '发票工单的货品编码错误，请处理好编码再导入'
                report_dic["error"].append(error)
                report_dic["false"] += 1
                work_order.mistake_tag = 15
                work_order.save()
                return report_dic

        return report_dic

    @action(methods=['post'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0, process_tag=5)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class OriInvoiceSubmitViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始发票工单
    list:
        返回原始发票工单列表
    update:
        更新原始发票工单信息
    destroy:
        删除原始发票工单信息
    create:
        创建原始发票工单信息
    partial_update:
        更新部分原始发票工单字段
    """
    serializer_class = OriInvoiceSerializer
    filter_class = OriInvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_user_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriInvoice.objects.none()
        queryset = OriInvoice.objects.filter(order_status=1, sign_department=self.request.user.department).exclude(
            process_tag=7).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for work_order in check_list:
                check_fields = ['order_id', 'invoice_id', 'title', 'tax_id', 'phone', 'bank', 'account',
                                'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address']
                for key in check_fields:
                    value = getattr(work_order, key, None)
                    if value:
                        setattr(work_order, key, str(value).replace(' ', '').replace("'", '').replace('\n', ''))
                if not work_order.company:
                    data["error"].append("%s 没开票公司" % work_order.order_id)
                    work_order.mistake_tag = 1
                    work_order.save()
                    n -= 1
                    continue

                if work_order.amount <= 0:
                    data["error"].append("%s 没添加货品, 或者货品价格添加错误" % work_order.order_id)
                    work_order.mistake_tag = 2
                    work_order.save()
                    n -= 1
                    continue
                # 判断专票信息是否完整
                if work_order.order_category == 1:
                    if not any([work_order.phone, work_order.bank, work_order.account, work_order.address]):
                        data["error"].append("%s 专票信息缺" % work_order.order_id)
                        work_order.mistake_tag = 3
                        work_order.save()
                        n -= 1
                        continue
                if work_order.is_deliver == 1:
                    if not re.match(r'^[0-9-]+$', work_order.sent_smartphone):
                        data["error"].append("%s 收件人手机错误" % work_order.order_id)
                        work_order.mistake_tag = 4
                        work_order.save()
                        n -= 1
                        continue
                if not re.match(
                        "^([13598Y]{1})([12349]{1})([0-9ABCDEFGHJKLMNPQRTUWXY]{6})([0-9ABCDEFGHJKLMNPQRTUWXY]{9})([0-9ABCDEFGHJKLMNPQRTUWXY])$",
                        work_order.tax_id):
                    data["error"].append("%s 税号错误" % work_order.order_id)
                    work_order.mistake_tag = 13
                    work_order.save()
                    n -= 1
                    continue
                if not re.match(r"^[0-9A-Z,]+$", work_order.order_id):
                    data["error"].append("%s 源单号错误，只支持大写字母和数字以及英文逗号" % work_order.order_id)
                    work_order.mistake_tag = 16
                    work_order.save()
                    n -= 1
                    continue
                if not work_order.memorandum:
                    work_order.memorandum = ''
                work_order.submit_time = datetime.datetime.now()
                work_order.order_status = 2
                work_order.mistake_tag = 0
                work_order.process_tag = 0
                work_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = OriInvoiceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriInvoice.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request["data"].pop("page", None)
        request["data"].pop("allSelectTag", None)
        params = request.data
        f = OriInvoiceFilter(params)
        serializer = OriInvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        print(request)
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {
            '店铺': 'shop',
            '收款开票公司': 'company',
            '源单号': 'order_id',
            '发票类型': 'order_category',
            '发票抬头': 'title',
            '纳税人识别号': 'tax_id',
            '联系电话': 'phone',
            '银行名称': 'bank',
            '银行账号': 'account',
            '地址': 'address',
            '发票备注': 'remark',
            '收件人姓名': 'sent_consignee',
            '收件人手机': 'sent_smartphone',
            '收件城市': 'sent_city',
            '收件区县': 'sent_district',
            '收件地址': 'sent_address',
            '是否发顺丰': 'is_deliver',
            '工单留言': 'message',
            '货品编码': 'goods_id',
            '货品名称': 'goods_name',
            '数量': 'quantity',
            '含税单价': 'price',
            '用户昵称': 'nickname',
        }
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0, converters={u'货品编码': str})
                FILTER_FIELDS = ['店铺', '收款开票公司', '源单号', '发票类型', '发票抬头', '纳税人识别号', '联系电话', '银行名称',
                                 '银行账号', '地址', '发票备注', '收件人姓名', '收件人手机', '收件城市', '收件区县', '收件地址',
                                 '是否发顺丰', '工单留言', '货品编码', '货品名称', '数量', '含税单价', '用户昵称']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    columns_key[i] = columns_key[i].replace(' ', '').replace('=', '')

                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = OriInvoice.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic["error"].append(str(_ret_verify_field))
                    return report_dic

                # 更改一下DataFrame的表名称
                columns_key_ori = df.columns.values.tolist()
                ret_columns_key = dict(zip(columns_key_ori, columns_key))
                df.rename(columns=ret_columns_key, inplace=True)
                check_list = ['shop', 'company', 'order_id', 'order_category', 'title', 'tax_id', 'phone', 'bank',
                              'account', 'address', 'remark', 'sent_consignee', 'sent_smartphone',
                              'sent_city', 'sent_district', 'sent_address', 'is_deliver', 'goods_id']
                df_check = df[check_list]

                tax_ids = list(set(df_check.tax_id))
                for tax_id in tax_ids:
                    data_check = df_check[df_check.tax_id == tax_id]
                    check_list.pop()
                    if len(data_check.goods_id) != len(list(set(data_check.goods_id))):
                        error = '税号%s，货品重复，请剔除重复货品' % str(tax_id)
                        report_dic["error"].append(error)
                        return report_dic
                    for word in check_list:
                        check_word = data_check[word]
                        if np.any(check_word.isnull() == True):
                            continue
                        check_word = list(set(check_word))
                        if len(check_word) > 1:
                            error = '税号%s的%s不一致，相同税号%s必须相同' % (str(tax_id), str(word), str(word))
                            report_dic["error"].append(error)
                            return report_dic

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                for tax_id in tax_ids:
                    df_invoice = df[df.tax_id == tax_id]
                    _ret_list = df_invoice.to_dict(orient='records')
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        work_order = OriInvoice()

        if not re.match(r'^[0-9A-Z]+$', str(resource[0]['order_id'])):
            error = '源单号%s非法，请使用正确的源单号格式（只支持英文字母和数字组合）' % resource[0]['order_id']
            report_dic['error'].append(error)
            return report_dic
        else:
            work_order.order_id = resource[0]['order_id']

        _q_work_order = OriInvoice.objects.filter(order_id=str(resource[0]['order_id']))
        if not _q_work_order.exists():
            # 开始导入数据
            check_list = ['title', 'tax_id', 'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address',
                          'phone', 'bank', 'account', 'address', 'remark', 'message', 'nickname']

            _q_shop = Shop.objects.filter(name=resource[0]['shop'])
            if _q_shop.exists():
                work_order.shop = _q_shop[0]
            else:
                error = '店铺%s不存在，请使用正确的店铺名' % resource[0]['shop']
                report_dic['error'].append(error)
                return report_dic
            _q_company = Company.objects.filter(name=resource[0]['company'])
            if _q_company.exists():
                work_order.company = _q_company[0]
            else:
                error = '开票公司%s不存在，请使用正确的公司名' % resource[0]['company']
                report_dic['error'].append(error)
                return report_dic
            category = {
                '专票': 1,
                '普票': 2,
            }
            order_category = category.get(resource[0]['order_category'], None)
            if order_category:
                work_order.order_category = order_category

            else:
                error = '开票类型%s不存在，请使用正确的开票类型' % resource[0]['order_category']
                report_dic['error'].append(error)
                return report_dic

            _q_city = City.objects.filter(city=str(resource[0]['sent_city']))
            if _q_city.exists():
                work_order.sent_city = _q_city[0]
            else:
                error = '城市%s非法，请使用正确的二级城市名称' % resource[0]['sent_city']
                report_dic['error'].append(error)
                return report_dic

            logical_decision = {
                '是': 1,
                '否': 0,
            }
            is_deliver = logical_decision.get(resource[0]['is_deliver'], None)
            if is_deliver is None:
                error = '是否发顺丰字段：%s非法（只可以填是否）' % resource[0]['is_deliver']
                report_dic['error'].append(error)
                return report_dic
            else:
                work_order.is_deliver = is_deliver

            if order_category == 1:
                check_list = check_list[:10]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开专票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            elif order_category == 2:
                check_list = check_list[:6]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开普票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            if self.request.user.company:
                work_order.sign_company = self.request.user.company
            else:
                error = '账号公司未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            if self.request.user.department:
                work_order.sign_department = self.request.user.department
            else:
                error = '账号部门未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            for attr in check_list:
                if resource[0][attr]:
                    setattr(work_order, attr, resource[0][attr])

            try:
                work_order.creator = self.request.user.username
                work_order.process_tag = 7
                work_order.save()
                report_dic["successful"] += 1
            # 保存出错，直接错误条数计数加一。
            except Exception as e:
                report_dic["error"].append(e)
                report_dic["false"] += 1
                return report_dic
        else:
            work_order = _q_work_order[0]
            if work_order.order_status != 1:
                error = '此订单%s已经存在，请核实再导入' % (work_order.order_id)
                report_dic["error"].append(error)
                report_dic["false"] += 1
                return report_dic
            work_order.process_tag = 7
            work_order.save()
            all_goods_info = work_order.oriinvoicegoods_set.all()
            all_goods_info.delete()

        goods_ids = [row['goods_id'] for row in resource]
        goods_quantity = [row['quantity'] for row in resource]
        goods_prices = [row['price'] for row in resource]

        for goods_id, quantity, price in zip(goods_ids, goods_quantity, goods_prices):
            goods_order = OriInvoiceGoods()
            _q_goods_id = Goods.objects.filter(goods_id=goods_id)
            if _q_goods_id.exists():
                goods_order.goods_name = _q_goods_id[0]
                goods_order.goods_id = goods_id
                goods_order.quantity = quantity
                goods_order.price = price
                goods_order.invoice = work_order
                goods_order.creator = self.request.user.username
                try:
                    goods_order.save()
                    report_dic["successful"] += 1
                # 保存出错，直接错误条数计数加一。
                except Exception as e:
                    report_dic["error"].append(e)
                    report_dic["false"] += 1
                    work_order.mistake_tag = 15
                    work_order.save()
                    return report_dic
            else:
                error = '发票工单的货品编码错误，请处理好编码再导入'
                report_dic["error"].append(error)
                report_dic["false"] += 1
                work_order.mistake_tag = 15
                work_order.save()
                return report_dic

        return report_dic

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(order_status=0, process_tag=5)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def reject_dealer(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            reject_list.update(process_tag=7)
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        return Response(data)


class OriInvoiceHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始发票工单
    list:
        返回原始发票工单列表
    update:
        更新原始发票工单信息
    destroy:
        删除原始发票工单信息
    create:
        创建原始发票工单信息
    partial_update:
        更新部分原始发票工单字段
    """
    serializer_class = OriInvoiceSerializer
    filter_class = OriInvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_handler_oriinvoice']
    }

    def get_queryset(self):
        queryset = OriInvoice.objects.filter(order_status=2).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for work_order in check_list:
                if work_order.order_category == 1:
                    if int(work_order.amount) > int(work_order.company.special_invoice):
                        data["error"].append("%s 超限额的发票，用拆单递交" % work_order.order_id)
                        work_order.mistake_tag = 5
                        work_order.save()
                        n -= 1
                        continue
                else:
                    if int(work_order.amount) > int(work_order.company.spain_invoice):
                        data["error"].append("%s 超限额的发票，用拆单递交" % work_order.order_id)
                        work_order.mistake_tag = 5
                        work_order.save()
                        n -= 1
                        continue

                invoice_order = Invoice()
                copy_fields_order = ['shop', 'company', 'order_id', 'order_category', 'title', 'tax_id', 'phone',
                                     'bank', 'account', 'address', 'remark', 'sent_consignee', 'sent_smartphone',
                                     'sent_city', 'sent_district', 'sent_address', 'amount', 'is_deliver',
                                     'message', 'creator', 'sign_company', 'sign_department', 'nickname']

                for key in copy_fields_order:
                    value = getattr(work_order, key, None)
                    setattr(invoice_order, key, value)

                invoice_order.sent_province = work_order.sent_city.province
                invoice_order.creator = work_order.creator
                invoice_order.ori_amount = work_order.amount
                invoice_order.work_order = work_order
                try:
                    invoice_order.save()
                except Exception as e:
                    data["error"].append("%s 递交发票出错 %s" % (work_order.order_id, e))
                    work_order.mistake_tag = 6
                    work_order.save()
                    n -= 1
                    continue
                _q_goods = work_order.oriinvoicegoods_set.all()
                for good in _q_goods:
                    invoice_good = InvoiceGoods()
                    invoice_good.invoice = invoice_order
                    invoice_good.goods_nickname = good.goods_name.name
                    copy_fields_goods = ['goods_id', 'goods_name', 'quantity', 'price', 'sign_company',
                                         'sing_department', 'memorandum']
                    for key in copy_fields_goods:
                        value = getattr(good, key, None)
                        setattr(invoice_good, key, value)
                    try:
                        invoice_good.creator = work_order.creator
                        invoice_good.save()
                    except Exception as e:
                        data["error"].append("%s 生成发票货品出错 %s" % (work_order.order_id, e))
                        work_order.mistake_tag = 7
                        work_order.save()
                        continue

                work_order.order_status = 3
                work_order.mistake_tag = 0
                work_order.process_tag = 6

                work_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    @action(methods=['patch'], detail=False)
    def check_unpack(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for work_order in check_list:
                quota = 0
                error_tag = 0
                if work_order.order_category == 1:
                    if work_order.amount > work_order.company.special_invoice:
                        quota = work_order.company.special_invoice
                        work_order.mistake_tag = 5
                else:
                    if work_order.amount > work_order.company.spain_invoice:
                        quota = work_order.company.spain_invoice
                        work_order.mistake_tag = 5

                if work_order.mistake_tag == 5:
                    _q_goods = work_order.oriinvoicegoods_set.all()

                    l_name, l_quantity, l_price = [goods.goods_name for goods in _q_goods], [goods.quantity for goods in
                                                                                             _q_goods], [goods.price for
                                                                                                         goods in
                                                                                                         _q_goods]
                    if max(l_price) > quota:
                        data["error"].append("%s 此订单为无法拆单的超限额工单，需驳回修正" % work_order.order_id)
                        work_order.mistake_tag = 8
                        work_order.save()
                        n -= 1
                        continue
                    amounts = list(map(lambda x, y: x * y, l_quantity, l_price))
                    total_amount = 0
                    for i in amounts:
                        total_amount = total_amount + i

                    _rt_name = []
                    _rt_quantity = []
                    part_amount = quota - 1

                    groups = []

                    current_quantity = list(l_quantity)
                    loop_num = 0
                    while True:
                        loop_num += 1
                        if loop_num > 1500:
                            data["error"].append("%s 此订单拆单的出现死循环，需联系管理员调试处理" % work_order.order_id)
                            return None
                        if _rt_quantity == l_quantity:
                            break
                        group = {}
                        group_amount = 0
                        end_tag = 0
                        for i in range(len(l_name)):
                            if end_tag:
                                break
                            amount = current_quantity[i] * l_price[i]
                            if amount == 0:
                                continue
                            if (amount + group_amount) <= part_amount:
                                group[l_name[i]] = [current_quantity[i], l_price[i]]

                                if l_name[i] in _rt_name:
                                    goods_num = l_name.index(l_name[i])
                                    _rt_quantity[goods_num] = _rt_quantity[goods_num] + current_quantity[i]
                                else:
                                    _rt_name.append(l_name[i])
                                    _rt_quantity.append(current_quantity[i])
                                current_quantity[i] = 0
                                if group:
                                    group_amount = 0
                                    for k, v in group.items():
                                        group_amount = group_amount + v[0] * v[1]
                                if current_quantity[-1] == 0:
                                    groups.append(group)
                                    break
                            else:
                                for step in range(1, current_quantity[i] + 1):
                                    if (current_quantity[i] - step) == 0:
                                        groups.append(group)
                                        end_tag = 1
                                        break
                                    increment = current_quantity[i] - step
                                    amount = increment * l_price[i]
                                    if (amount + group_amount) <= part_amount:
                                        group[l_name[i]] = [increment, l_price[i]]

                                        if l_name[i] in _rt_name:
                                            goods_num = l_name.index(l_name[i])
                                            _rt_quantity[goods_num] = _rt_quantity[goods_num] + increment
                                            current_quantity[i] = current_quantity[i] - increment
                                        else:
                                            _rt_name.append(l_name[i])
                                            _rt_quantity.append(increment)
                                            current_quantity[i] = current_quantity[i] - increment
                                        groups.append(group)
                                        end_tag = 1
                                        break

                    invoice_quantity = len(groups)
                    for invoice_num in range(invoice_quantity):
                        invoice_order = Invoice()
                        series_number = invoice_num + 1
                        order_id = '%s-%s' % (work_order.order_id, series_number)

                        _q_invoice_order = Invoice.objects.filter(order_id=order_id)
                        if _q_invoice_order.exists():
                            data["error"].append("%s 发票工单重复生成发票订单，检查后处理" % work_order.order_id)
                            work_order.mistake_tag = 9
                            work_order.save()
                            n -= 1
                            error_tag = 1
                            continue
                        invoice_order.order_id = order_id

                        invoice_order.work_order = work_order
                        copy_fields_order = ['shop', 'company', 'order_category', 'title', 'tax_id', 'phone',
                                             'bank', 'account', 'address', 'remark', 'sent_consignee',
                                             'sent_smartphone', 'sent_city', 'sent_district', 'sent_address',
                                             'is_deliver', 'message', 'sign_company', 'sign_department', 'creator',
                                             'nickname']
                        for key in copy_fields_order:
                            value = getattr(work_order, key, None)
                            setattr(invoice_order, key, value)

                        invoice_order.sent_province = work_order.sent_city.province
                        invoice_order.creator = work_order.creator
                        invoice_order.ori_amount = work_order.amount
                        try:
                            invoice_order.save()
                        except Exception as e:
                            data["error"].append("%s 生成发票订单出错，请仔细检查 %s" % (work_order.order_id, e))
                            work_order.mistake_tag = 10
                            work_order.save()
                            error_tag = 1
                            n -= 1
                            continue
                        current_amount = 0
                        for goods, detail in groups[invoice_num].items():
                            goods_order = InvoiceGoods()
                            current_amount = current_amount + (detail[0] * detail[1])
                            goods_order.invoice = invoice_order
                            goods_order.goods_name = goods
                            goods_order.goods_nickname = goods.name
                            goods_order.goods_id = goods.goods_id
                            goods_order.quantity = detail[0]
                            goods_order.price = detail[1]
                            goods_order.memorandum = '来源 %s 的第 %s 张发票' % (work_order.order_id, invoice_num + 1)

                            try:
                                goods_order.creator = work_order.creator
                                goods_order.save()
                            except Exception as e:
                                data["error"].append("%s 生成发票订单货品出错，请仔细检查 %s" % (work_order.order_id, e))
                                work_order.mistake_tag = 11
                                work_order.save()
                                n -= 1
                                error_tag = 1
                                continue

                        invoice_order.amount = current_amount
                        invoice_order.save()

                    if error_tag == 1:
                        n -= 1
                        continue

                    work_order.order_status = 3
                    work_order.mistake_tag = 0
                    work_order.process_tag = 6
                    work_order.save()

                else:
                    data["error"].append("%s 非超额订单，请用未超限额模式审核。" % work_order.order_id)
                    work_order.mistake_tag = 0
                    work_order.save()
                    n -= 1
                    continue
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 2
        if all_select_tag:
            handle_list = OriInvoiceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = OriInvoice.objects.filter(id__in=order_ids, order_status=2)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = OriInvoiceFilter(params)
        serializer = OriInvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        print(request)
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {
            '店铺': 'shop',
            '收款开票公司': 'company',
            '源单号': 'order_id',
            '发票类型': 'order_category',
            '发票抬头': 'title',
            '纳税人识别号': 'tax_id',
            '联系电话': 'phone',
            '银行名称': 'bank',
            '银行账号': 'account',
            '地址': 'address',
            '发票备注': 'remark',
            '收件人姓名': 'sent_consignee',
            '收件人手机': 'sent_smartphone',
            '收件城市': 'sent_city',
            '收件区县': 'sent_district',
            '收件地址': 'sent_address',
            '是否发顺丰': 'is_deliver',
            '工单留言': 'message',
            '货品编码': 'goods_id',
            '货品名称': 'goods_name',
            '数量': 'quantity',
            '含税单价': 'price',
            '用户昵称': 'nickname',
        }
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0, converters={u'货品编码': str})
                FILTER_FIELDS = ['店铺', '收款开票公司', '源单号', '发票类型', '发票抬头', '纳税人识别号', '联系电话', '银行名称',
                                 '银行账号', '地址', '发票备注', '收件人姓名', '收件人手机', '收件城市', '收件区县', '收件地址',
                                 '是否发顺丰', '工单留言', '货品编码', '货品名称', '数量', '含税单价', '用户昵称']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    columns_key[i] = columns_key[i].replace(' ', '').replace('=', '')

                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = OriInvoice.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic["error"].append(str(_ret_verify_field))
                    return report_dic

                # 更改一下DataFrame的表名称
                columns_key_ori = df.columns.values.tolist()
                ret_columns_key = dict(zip(columns_key_ori, columns_key))
                df.rename(columns=ret_columns_key, inplace=True)
                check_list = ['shop', 'company', 'order_id', 'order_category', 'title', 'tax_id', 'phone', 'bank',
                              'account', 'address', 'remark', 'sent_consignee', 'sent_smartphone',
                              'sent_city', 'sent_district', 'sent_address', 'is_deliver', 'goods_id']
                df_check = df[check_list]

                tax_ids = list(set(df_check.tax_id))
                for tax_id in tax_ids:
                    data_check = df_check[df_check.tax_id == tax_id]
                    check_list.pop()
                    if len(data_check.goods_id) != len(list(set(data_check.goods_id))):
                        error = '税号%s，货品重复，请剔除重复货品' % str(tax_id)
                        report_dic["error"].append(error)
                        return report_dic
                    for word in check_list:
                        check_word = data_check[word]
                        if np.any(check_word.isnull() == True):
                            continue
                        check_word = list(set(check_word))
                        if len(check_word) > 1:
                            error = '税号%s的%s不一致，相同税号%s必须相同' % (str(tax_id), str(word), str(word))
                            report_dic["error"].append(error)
                            return report_dic

                # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                for tax_id in tax_ids:
                    df_invoice = df[df.tax_id == tax_id]
                    _ret_list = df_invoice.to_dict(orient='records')
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        work_order = OriInvoice()

        if not re.match(r'^[0-9A-Z]+$', str(resource[0]['order_id'])):
            error = '源单号%s非法，请使用正确的源单号格式（只支持英文字母和数字组合）' % resource[0]['order_id']
            report_dic['error'].append(error)
            return report_dic
        else:
            work_order.order_id = resource[0]['order_id']

        _q_work_order = OriInvoice.objects.filter(order_id=str(resource[0]['order_id']))
        if not _q_work_order.exists():
            # 开始导入数据
            check_list = ['title', 'tax_id', 'sent_consignee', 'sent_smartphone', 'sent_district', 'sent_address',
                          'phone', 'bank', 'account', 'address', 'remark', 'message', 'nickname']

            _q_shop = Shop.objects.filter(name=resource[0]['shop'])
            if _q_shop.exists():
                work_order.shop = _q_shop[0]
            else:
                error = '店铺%s不存在，请使用正确的店铺名' % resource[0]['shop']
                report_dic['error'].append(error)
                return report_dic
            _q_company = Company.objects.filter(name=resource[0]['company'])
            if _q_company.exists():
                work_order.company = _q_company[0]
            else:
                error = '开票公司%s不存在，请使用正确的公司名' % resource[0]['company']
                report_dic['error'].append(error)
                return report_dic
            category = {
                '专票': 1,
                '普票': 2,
            }
            order_category = category.get(resource[0]['order_category'], None)
            if order_category:
                work_order.order_category = order_category

            else:
                error = '开票类型%s不存在，请使用正确的开票类型' % resource[0]['order_category']
                report_dic['error'].append(error)
                return report_dic

            _q_city = City.objects.filter(city=str(resource[0]['sent_city']))
            if _q_city.exists():
                work_order.sent_city = _q_city[0]
            else:
                error = '城市%s非法，请使用正确的二级城市名称' % resource[0]['sent_city']
                report_dic['error'].append(error)
                return report_dic

            logical_decision = {
                '是': 1,
                '否': 0,
            }
            is_deliver = logical_decision.get(resource[0]['is_deliver'], None)
            if is_deliver is None:
                error = '是否发顺丰字段：%s非法（只可以填是否）' % resource[0]['is_deliver']
                report_dic['error'].append(error)
                return report_dic
            else:
                work_order.is_deliver = is_deliver

            if order_category == 1:
                check_list = check_list[:10]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开专票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            elif order_category == 2:
                check_list = check_list[:6]
                for k in check_list:
                    if not resource[0][k]:
                        error = '%s非法，开普票请把必填项补全' % k
                        report_dic['error'].append(error)
                        return report_dic
            if self.request.user.company:
                work_order.sign_company = self.request.user.company
            else:
                error = '账号公司未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            if self.request.user.department:
                work_order.sign_department = self.request.user.department
            else:
                error = '账号部门未设置或非法，联系管理员处理'
                report_dic['error'].append(error)
                return report_dic

            for attr in check_list:
                if resource[0][attr]:
                    setattr(work_order, attr, resource[0][attr])

            try:
                work_order.creator = self.request.user.username
                work_order.process_tag = 7
                work_order.save()
                report_dic["successful"] += 1
            # 保存出错，直接错误条数计数加一。
            except Exception as e:
                report_dic["error"].append(e)
                report_dic["false"] += 1
                return report_dic
        else:
            work_order = _q_work_order[0]
            if work_order.order_status != 1:
                error = '此订单%s已经存在，请核实再导入' % (work_order.order_id)
                report_dic["error"].append(error)
                report_dic["false"] += 1
                return report_dic
            work_order.process_tag = 7
            work_order.save()
            all_goods_info = work_order.oriinvoicegoods_set.all()
            all_goods_info.delete()

        goods_ids = [row['goods_id'] for row in resource]
        goods_quantity = [row['quantity'] for row in resource]
        goods_prices = [row['price'] for row in resource]

        for goods_id, quantity, price in zip(goods_ids, goods_quantity, goods_prices):
            goods_order = OriInvoiceGoods()
            _q_goods_id = Goods.objects.filter(goods_id=goods_id)
            if _q_goods_id.exists():
                goods_order.goods_name = _q_goods_id[0]
                goods_order.goods_id = goods_id
                goods_order.quantity = quantity
                goods_order.price = price
                goods_order.invoice = work_order
                goods_order.creator = self.request.user.username
                try:
                    goods_order.save()
                    report_dic["successful"] += 1
                # 保存出错，直接错误条数计数加一。
                except Exception as e:
                    report_dic["error"].append(e)
                    report_dic["false"] += 1
                    work_order.mistake_tag = 15
                    work_order.save()
                    return report_dic
            else:
                error = '发票工单的货品编码错误，请处理好编码再导入'
                report_dic["error"].append(error)
                report_dic["false"] += 1
                work_order.mistake_tag = 15
                work_order.save()
                return report_dic

        return report_dic

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for work_order in reject_list:
                if work_order.memorandum:
                    work_order.order_status = 1
                    work_order.process_tag = 5
                    work_order.save()
                else:
                    data["error"].append("驳回时，工单反馈不可为空！")
                    n -= 1
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = n
        data["false"] = len(reject_list) - n
        return Response(data)


class OriInvoiceManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定原始发票工单
    list:
        返回原始发票工单列表
    update:
        更新原始发票工单信息
    destroy:
        删除原始发票工单信息
    create:
        创建原始发票工单信息
    partial_update:
        更新部分原始发票工单字段
    """
    serializer_class = OriInvoiceSerializer
    filter_class = OriInvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_oriinvoice']
    }

    def get_queryset(self):
        if not self.request:
            return OriInvoice.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = OriInvoice.objects.all().order_by("id")
        else:
            queryset = OriInvoice.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['get'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        params = request.query_params
        f = OriInvoiceFilter(params)
        serializer = OriInvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)


class OriInvoiceGoodsViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    queryset = OriInvoiceGoods.objects.all().order_by("id")
    serializer_class = OriInvoiceGoodsSerializer
    filter_class = OriInvoiceGoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_oriinvoice']
    }


class InvoiceHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = InvoiceSerializer
    filter_class = InvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_handler_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Invoice.objects.none()
        queryset = Invoice.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for invoice_order in check_list:
                if not invoice_order.invoice_id:
                    invoice_order.mistake_tag = 1
                    invoice_order.save()
                    raise serializers.ValidationError("%s 工单中此单还没有开票，不可以审核" % invoice_order.order_id)

            _work_orders = set([invoice_order.work_order for invoice_order in check_list])
            for check_order in _work_orders:
                _check_invoices = check_order.invoice_set.all()
                for check_invoice in _check_invoices:
                    if not check_invoice.invoice_id:
                        _check_invoices.update(mistake_tag = 1)
                        raise serializers.ValidationError("%s 工单中此单还存在未开票拆分单据，同一个工单必须全部开票之后才可以审核！" % check_order.order_id)
            for work_order in _work_orders:
                _q_work_order = DeliverOrder.objects.filter(work_order=work_order)
                if not _q_work_order:
                    deliver_order = DeliverOrder()
                    deliver_order.work_order = work_order
                    deliver_order.shop = work_order.shop.name
                    deliver_order.consignee = work_order.sent_consignee
                    deliver_order.address = work_order.sent_address
                    deliver_order.smartphone = work_order.sent_smartphone
                    deliver_order.province = invoice_order.sent_city.province.name
                    deliver_order.city = invoice_order.sent_city.name
                    if work_order.nickname:
                        deliver_order.nickname = work_order.nickname
                    else:
                        deliver_order.nickname = work_order.sent_consignee

                    if work_order.is_deliver:
                        deliver_order.logistics = '顺丰'
                    else:
                        deliver_order.logistics = '申通'
                    deliver_order.remark = deliver_order.logistics
                    if work_order.sent_district:
                        _q_district = District.objects.filter(city=work_order.sent_city,
                                                              district=work_order.sent_district)
                        if _q_district.exists():
                            deliver_order.district = _q_district[0].name
                        else:
                            deliver_order.district = '其他区'
                    _q_invoice_orders = work_order.invoice_set.all()
                    invoice_ids = [invoice.invoice_id for invoice in _q_invoice_orders]
                    invoice_num = len(invoice_ids)
                    if invoice_num < 4:
                        deliver_order.ori_order_id = reduce(lambda x, y: x + "," + y, invoice_ids)
                        deliver_order.message = '%s%s共%s张' % (
                        work_order.sign_department.name, work_order.creator, invoice_num)
                    else:
                        deliver_order.ori_order_id = reduce(lambda x, y: x + "," + y, invoice_ids[:3])
                        deliver_order.message = '%s%s共%s张(发票号最大显示3个，完整见UT发票订单)' % (
                        work_order.sign_department.name, work_order.creator, invoice_num)
                    try:
                        deliver_order.save()
                    except Exception as e:
                        data["error"].append("%s 生成快递运单失败，请仔细检查 %s" % (invoice_order.order_id, e))
                        work_order.invoice_set.all().update(mistake_tag = 2)
                        _work_orders.remove(work_order)
                        continue
            completed_num = 0
            for completed_work_order in _work_orders:
                completed_invoice = completed_work_order.invoice_set.all()
                completed_num += completed_invoice.count()
                completed_invoice.update(order_status=2, mistake_tag=0, process_tag=4)

        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = completed_num
        data["false"] = n - completed_num
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = InvoiceFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = Invoice.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = InvoiceFilter(params)
        serializer = InvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def reject(self, request, *args, **kwargs):
        params = request.data
        reject_list = self.get_handle_list(params)
        n = len(reject_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            _work_orders = set([invoice_order.work_order for invoice_order in reject_list])
            for work_order in _work_orders:
                mistake_tag = 0
                _q_invoice_orders = work_order.invoice_set.all()
                for invoice_order in _q_invoice_orders:
                    if invoice_order.order_status != 1 or invoice_order.invoice_id:
                        n -= 1
                        raise serializers.ValidationError("%s 请确保此源工单对应的所有的发票订单都为未开票状态。" % work_order)
                for invoice_order in _q_invoice_orders:
                    try:
                        invoice_order.invoicegoods_set.all().delete()
                    except Exception as e:
                        data["error"].append("%s 删除货品信息失败。错误：%s" % (invoice_order, e))
                        invoice_order.mistake_tag = 4
                        invoice_order.save()
                        mistake_tag = 1
                        continue
                if mistake_tag:
                    _work_orders.remove(work_order)
                    data["error"].append("%s 此订单驳回出错!" % work_order)
                    continue
            completed_num = 0
            for completed_work_order in _work_orders:
                completed_invoice = completed_work_order.invoice_set.all()
                completed_num += completed_invoice.count()
                try:
                    completed_invoice.delete()
                    completed_work_order.order_status = 2
                    completed_work_order.save()
                except Exception as e:
                    data["error"].append("删除订单失败。错误：%s" % e)
                    continue
        else:
            raise serializers.ValidationError("没有可驳回的单据！")
        data["successful"] = completed_num
        data["false"] = n - completed_num
        return Response(data)


class InvoiceManageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品明细
    list:
        返回货品明细
    update:
        更新货品明细
    destroy:
        删除货品明细
    create:
        创建货品明细
    partial_update:
        更新部分货品明细
    """
    serializer_class = InvoiceSerializer
    filter_class = InvoiceFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_invoice']
    }

    def get_queryset(self):
        if not self.request:
            return Invoice.objects.none()
        user = self.request.user
        if user.is_our:
            queryset = Invoice.objects.all().order_by("id")
        else:
            queryset = Invoice.objects.filter(creator=user.username).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        user = self.request.user
        if not user.is_superuser:
            if user.is_our:
                request.data["sign_department"] = user.department
            else:
                request.data["creator"] = user.username
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = InvoiceFilter(params)
        serializer = InvoiceSerializer(f.qs, many=True)
        return Response(serializer.data)


class DeliverHandleViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定发票快递单据
    list:
        返回发票快递明细
    update:
        更新发票快递单据
    destroy:
        删除发票快递单据
    create:
        创建发票快递单据
    partial_update:
        更新部分发票快递单据信息
    """
    serializer_class = DeliverOrderSerializer
    filter_class = DeliverOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_deliverorder']
    }

    def get_queryset(self):
        if not self.request:
            return DeliverOrder.objects.none()
        queryset = DeliverOrder.objects.filter(order_status=1).order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def check(self, request, *args, **kwargs):
        print(request)
        params = request.data
        check_list = self.get_handle_list(params)
        n = len(check_list)
        data = {
            "successful": 0,
            "false": 0,
            "error": []
        }
        if n:
            for deliver_order in check_list:
                if deliver_order.process_tag == 0:
                    if not deliver_order.track_no or not deliver_order.logistics:
                        data["error"].append("%s 此单还没有打印，不能递交" % deliver_order.ori_order_id)
                        deliver_order.mistake_tag = 1
                        deliver_order.save()
                        n -= 1
                        continue
                    else:
                        deliver_order.process_tag = 1
                deliver_order.work_order.memorandum = str(deliver_order.work_order.memorandum) + '%s：%s' % (deliver_order.logistics, deliver_order.track_no)
                deliver_order.work_order.process_tag = 6
                deliver_order.work_order.mistake_tag = 0
                deliver_order.work_order.save()
                _q_invoice_orders = deliver_order.work_order.invoice_set.all()
                if _q_invoice_orders.exists():
                    try:
                        _q_invoice_orders.update(track_no='%s：%s' % (deliver_order.logistics, deliver_order.track_no), process_tag=5)
                    except Exception as e:
                        data["error"].append("%s 回写快递单号失败，请仔细检查 %s" % (deliver_order.ori_order_id), e)
                        deliver_order.mistake_tag = 2
                        deliver_order.save()
                        n -= 1
                        continue
                deliver_order.order_status = 2
                deliver_order.mistake_tag = 0
                deliver_order.save()
        else:
            raise serializers.ValidationError("没有可审核的单据！")
        data["successful"] = n
        data["false"] = len(check_list) - n
        return Response(data)

    def get_handle_list(self, params):
        params.pop("page", None)
        all_select_tag = params.pop("allSelectTag", None)
        params["order_status"] = 1
        if all_select_tag:
            handle_list = DeliverOrderFilter(params).qs
        else:
            order_ids = params.pop("ids", None)
            if order_ids:
                handle_list = DeliverOrder.objects.filter(id__in=order_ids, order_status=1)
            else:
                handle_list = []
        return handle_list

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data["order_status"] = 1
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DeliverOrderFilter(params)
        serializer = DeliverOrderSerializer(f.qs, many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        print(request)
        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(file)
        else:
            data = {
                "error": "上传文件未找到！"
            }
        return Response(data)

    def handle_upload_file(self, _file):
        INIT_FIELDS_DIC = {"原始单号": "ori_order_id", "物流公司": "logistics", "物流单号": "track_no"}
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            with pd.ExcelFile(_file) as xls:
                df = pd.read_excel(xls, sheet_name=0, converters={u'原始单号': str})
                FILTER_FIELDS = ['原始单号', '物流公司', '物流单号']

                try:
                    df = df[FILTER_FIELDS]
                except Exception as e:
                    report_dic["error"].append(e)
                    return report_dic

                # 获取表头，对表头进行转换成数据库字段名
                columns_key = df.columns.values.tolist()
                for i in range(len(columns_key)):
                    if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                        columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

                # 验证一下必要的核心字段是否存在
                _ret_verify_field = DeliverOrder.verify_mandatory(columns_key)
                if _ret_verify_field is not None:
                    report_dic['error'].append(_ret_verify_field)
                    return report_dic

                # 更改一下DataFrame的表名称
                columns_key_ori = df.columns.values.tolist()
                ret_columns_key = dict(zip(columns_key_ori, columns_key))
                df.rename(columns=ret_columns_key, inplace=True)

                # 更改一下DataFrame的表名称
                num_end = 0
                step = 300
                step_num = int(len(df) / step) + 2
                i = 1
                while i < step_num:
                    num_start = num_end
                    num_end = step * i
                    intermediate_df = df.iloc[num_start: num_end]

                    # 获取导入表格的字典，每一行一个字典。这个字典最后显示是个list
                    _ret_list = intermediate_df.to_dict(orient='records')
                    intermediate_report_dic = self.save_resources(_ret_list)
                    for k, v in intermediate_report_dic.items():
                        if k == "error":
                            if intermediate_report_dic["error"]:
                                report_dic[k].append(v)
                        else:
                            report_dic[k] += v
                    i += 1
                return report_dic

        else:
            error = "只支持excel文件格式！"
            report_dic["error"].append(error)
            return report_dic

    def save_resources(self, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}

        for row in resource:
            # 字符串字段去特殊字符
            for key, value in row.items():
                row[key] = str(value).replace(' ', '').replace("'", '').replace('\n', '')
            _q_deliver_order = DeliverOrder.objects.filter(ori_order_id=row['ori_order_id'])
            if _q_deliver_order.exists():
                deliver_order = _q_deliver_order[0]
                deliver_order.logistics = row['logistics']
                deliver_order.track_no = row['track_no']

            else:
                report_dic["discard"] += 1
                report_dic["error"].append("%s原始单号无法找到发货单" % row['ori_order_id'])
                continue

            try:
                deliver_order.process_tag = 1
                deliver_order.save()
                report_dic["successful"] += 1
            # 保存出错，直接错误条数计数加一。
            except Exception as e:
                report_dic["false"] += 1
                report_dic["error"].append(e)
        return report_dic


class DelivermanageViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定发票快递单据
    list:
        返回发票快递明细
    update:
        更新发票快递单据
    destroy:
        删除发票快递单据
    create:
        创建发票快递单据
    partial_update:
        更新部分发票快递单据信息
    """
    serializer_class = DeliverOrderSerializer
    filter_class = DeliverOrderFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['woinvoice.view_deliverorder']
    }

    def get_queryset(self):
        if not self.request:
            return DeliverOrder.objects.none()
        queryset = DeliverOrder.objects.all().order_by("id")
        return queryset

    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        # raise serializers.ValidationError("看下失败啥样！")
        request.data["order_status"] = 1
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = DeliverOrderFilter(params)
        serializer = DeliverOrderSerializer(f.qs, many=True)
        return Response(serializer.data)




