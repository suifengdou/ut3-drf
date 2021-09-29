import pandas as pd
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import GoodsCategorySerializer, GoodsSerializer
from .filters import GoodsFilter, GoodsCategoryFilter
from .models import GoodsCategory, Goods
from ut3.permissions import Permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers


class GoodsViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品
    list:
        返回货品列表
    update:
        更新货品信息
    destroy:
        删除货品信息
    create:
        创建货品信息
    partial_update:
        更新部分货品字段
    """
    queryset = Goods.objects.all().order_by("id")
    serializer_class = GoodsSerializer
    filter_class = GoodsFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }


    @action(methods=['patch'], detail=False)
    def export(self, request, *args, **kwargs):
        request.data.pop("page", None)
        request.data.pop("allSelectTag", None)
        params = request.data
        f = GoodsFilter(params)
        serializer = GoodsSerializer(f.qs[:2000], many=True)
        return Response(serializer.data)

    @action(methods=['patch'], detail=False)
    def excel_import(self, request, *args, **kwargs):

        file = request.FILES.get('file', None)
        if file:
            data = self.handle_upload_file(request, file)
        else:
            data = {
                "error": "上传文件未找到！"
            }

        return Response(data)

    def handle_upload_file(self, request, _file):
        ALLOWED_EXTENSIONS = ['xls', 'xlsx']
        INIT_FIELDS_DIC = {
            "货品编码": "goods_id",
            "货品名称": "name",
            "货品类别": "category",
            "货品属性": "goods_attribute",
            "机器排序": "goods_number",
            "规格": "size",
            "长": "width",
            "宽": "height",
            "高": "depth",
            "重量": "weight",
            "爆炸图号": "catalog_num"
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["货品编码", "货品名称", "货品类别", "货品属性", "机器排序", "规格", "长", "宽", "高", "重量", "爆炸图号"]

            try:
                df = df[FILTER_FIELDS]
            except Exception as e:
                report_dic["error"].append("必要字段不全或者错误")
                return report_dic

            # 获取表头，对表头进行转换成数据库字段名
            columns_key = df.columns.values.tolist()
            for i in range(len(columns_key)):
                if INIT_FIELDS_DIC.get(columns_key[i], None) is not None:
                    columns_key[i] = INIT_FIELDS_DIC.get(columns_key[i])

            # 验证一下必要的核心字段是否存在
            _ret_verify_field = Goods.verify_mandatory(columns_key)
            if _ret_verify_field is not None:
                return _ret_verify_field

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
        attr_dic = {
            '整机': 1,
            '配件': 2,
            '礼品': 3
        }
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        order_fields = ["name", "category", "goods_attribute", "goods_number", "size", "width",
                        "height", "depth", "weight", "catalog_num"]
        for row in resource:
            _q_goods = Goods.objects.filter(goods_id=row["goods_id"])
            if _q_goods.exists():
                order = _q_goods[0]
            else:
                order = Goods()
                order.goods_id = row["goods_id"]

            if not all([row["goods_id"], row["name"], row["category"], row["goods_attribute"], row["goods_number"]]):
                report_dic["false"] += 1
                report_dic["error"].append("表格中必填项：货品编码 货品名称 货品类别 货品属性 机器排序，出错！")
                continue
            error_tag = 0
            for field in order_fields:
                if field == "goods_attribute":
                    value = attr_dic.get(row["goods_attribute"], None)
                    if not value:
                        report_dic["false"] += 1
                        report_dic["error"].append("%s 表格中货品类别出错！" % row["goods_id"])
                        error_tag = 1
                        break
                elif field == "category":
                    _q_category = GoodsCategory.objects.filter(name=row["category"])
                    if _q_category.exists():
                        value = _q_category[0]
                    else:
                        if not value:
                            report_dic["false"] += 1
                            report_dic["error"].append("%s 表格中货品属性出错！"% row["goods_id"])
                            error_tag = 1
                            break
                else:
                    value = row[field]
                if str(value) == "nan":
                    value = None
                setattr(order, field, value)
            if error_tag:
                continue
            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["goods_id"])
                report_dic["false"] += 1
        return report_dic


class GoodsCategoryViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定货品类别
    list:
        返回货品类别列表
    update:
        更新货品类别信息
    destroy:
        删除货品类别信息
    create:
        创建货品类别信息
    partial_update:
        更新部分货品类别字段
    """
    queryset = GoodsCategory.objects.all().order_by("id")
    serializer_class = GoodsCategorySerializer
    filter_class = GoodsCategoryFilter
    filter_fields = "__all__"
    permission_classes = (IsAuthenticated, Permissions)
    extra_perm_map = {
        "GET": ['goods.view_goods']
    }
