# -*- coding: utf-8 -*-
import datetime
import hashlib
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import CompanySerializer
from .filters import CompanyFilter
from .models import Company
from ut3.permissions import Permissions
import oss2
from rest_framework.decorators import action
from rest_framework.response import Response
from ut3.settings import OSS_CONFIG
from itertools import islice
from apps.utils.oss.aliyunoss import AliyunOSS


class CompanyViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定公司
    list:
        返回公司列表
    update:
        更新公司信息
    destroy:
        删除公司信息
    create:
        创建公司信息
    partial_update:
        更新部分公司字段
    """
    queryset = Company.objects.all().order_by("id")
    serializer_class = CompanySerializer
    filter_class = CompanyFilter
    filter_fields = ("name", "company", "tax_fil_number", "order_status", "category", "spain_invoice",
                     "special_invoice", "discount_rate", "create_time", "update_time", "is_delete", "creator")
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['company.view_company']
    }


    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):
        list = []  # myfile is the key of a multi value dictionary, values are the uploaded files
        files = request.FILES.getlist("files")

        file = request.FILES["files"]
        num = len(request.FILES["files"])
        if not file:
        #     data = self.handle_upload_file(request, file)
        # else:
            data = {
                "error": "上传文件未找到！"
            }

        data = request.data
        num1 = len(request.data["files"])


        prefix = "ut3s1/base/company"
        a_oss = AliyunOSS(prefix, file)
        file_urls = a_oss.upload()

        auth = oss2.Auth(OSS_CONFIG["AccessKeyId"], OSS_CONFIG["AccessKeySecret"])
        cname = OSS_CONFIG["cname"]
        endpoint = OSS_CONFIG["endpoint"]
        bucket = oss2.Bucket(auth, endpoint, OSS_CONFIG["bucket_name"])
        c_time = datetime.datetime.now()
        suffix = str(file.name).split(".")[1]
        serial_nuber = str(hashlib.md5(suffix[0].encode(encoding='UTF-8')).hexdigest())
        file_name = '%s%s%s%s' % (c_time.year, c_time.month, c_time.day, serial_nuber)
        object_name = '%s/%s/%s/%s.%s' % (c_time.year, c_time.month, c_time.day, file_name, suffix)
        result = bucket.put_object(object_name, file)

        for b in islice(oss2.ObjectIterator(bucket), 10):
            print(b.key)
        return Response(data)

    def handle_upload_file(self, request, _file):
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)
            columns_key_ori = df.columns.values.tolist()
            filter_fields = ["快递单号", "工单事项类型", "快递公司", "初始问题信息", "备注"]
            INIT_FIELDS_DIC = {
                "快递单号": "track_id",
                "工单事项类型": "category",
                "快递公司": "company",
                "初始问题信息": "information",
                "备注": "memo"
            }
            result_keys = []
            for keywords in columns_key_ori:
                if keywords in filter_fields:
                    result_keys.append(keywords)

            try:
                df = df[result_keys]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            result_columns = []
            for keywords in columns_key:
                result_columns.append(INIT_FIELDS_DIC.get(keywords, None))

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = ExpressWorkOrder.verify_mandatory(result_columns)
            if _ret_verify_field is not None:
                return _ret_verify_field

            # 更改一下DataFrame的表名称
            ret_columns_key = dict(zip(columns_key, result_columns))
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
                intermediate_report_dic = self.save_resources(request, _ret_list)
                for k, v in intermediate_report_dic.items():
                    if k == "error":
                        if intermediate_report_dic["error"]:
                            report_dic[k].append(v)
                    else:
                        report_dic[k] += v
                i += 1
            return report_dic

        else:
            report_dic["error"].append('只支持excel文件格式！')
            return report_dic

    @staticmethod
    def save_resources(request, resource):
        # 设置初始报告
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        error = report_dic["error"].append
        category_list = {
            "截单退回": 1,
            "无人收货": 2,
            "客户拒签": 3,
            "修改地址": 4,
            "催件派送": 5,
            "虚假签收": 6,
            "丢件破损": 7,
            "其他异常": 8
        }
        user = request.user

        for row in resource:

            order_fields = ["track_id", "category", "company", "information", "memo"]
            row["category"] = category_list.get(row["category"], None)
            if not row["category"]:
                error("%s 单据类型错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            _q_company = Company.objects.filter(name=row["company"])
            if _q_company.exists():
                row["company"] = _q_company[0]
            else:
                error("%s 快递错误" % row["track_id"])
                report_dic["false"] += 1
                continue
            order = ExpressWorkOrder()
            order.is_forward = user.is_our

            for field in order_fields:
                setattr(order, field, row[field])
            order.track_id = re.sub("[!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.track_id).strip())

            try:
                order.creator = user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["track_id"])
                report_dic["false"] += 1

        return report_dic