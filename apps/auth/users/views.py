import pandas as pd
from django.shortcuts import render
from rest_framework import viewsets, mixins, response
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from .filters import UserFilter
from ut3.permissions import Permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from django.contrib.auth import authenticate

User = get_user_model()

class UserViewset(viewsets.ModelViewSet):
    """
    retrieve:
        返回指定用户
    list:
        返回用户列表
    update:
        更新用户信息
    destroy:
        删除用户信息
    create:
        创建用户信息
    partial_update:
        更新部分用户字段
    """
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    filter_class = UserFilter
    filter_fields = ("username", "creator", "create_time", "is_staff", "is_active")
    permission_classes = (IsAuthenticated,)
    # extra_perm_map = {
    #     "GET": ['users.view_userprofile']
    # }

    def list(self, request, *args, **kwargs):
        return super(UserViewset, self).list(request, *args, **kwargs)

    @action(methods=["get"], detail=False)
    def get_user_info(self, request, *args, **kwargs):
        user = request.user
        error = {"id": -1, "name": "错误"}
        try:
            company = {
                "id": user.company.id,
                "name": user.company.name
            }
        except:
            company = error
        try:
            department = {
                "id": user.department.id,
                "name": user.department.name
            }

        except:
            department = error
        if user.is_superuser:
            roles = ["AllPrivileges"]
        else:
            result_permissions = filter(lambda x: "view" in x, user.get_group_permissions())
            roles = list(result_permissions)
        data = {
             "name": user.username,
            "roles": roles,
            "avatar": 'http://ut3.xiaogou777.com/avatar.png',
            "introduction": "UT3用户",
            "company": company,
            "department": department
        }
        return response.Response(data)

    @action(methods=["patch"], detail=False)
    def change_password(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        if data["new_password"] != data["pwd_repeat"]:
            raise serializers.ValidationError("新密码和确认密码不一致！")
        if len(data["new_password"]) < 5 or len(data["new_password"]) > 15:
            raise serializers.ValidationError("新密码最少5位，最大14位！")
        check_user = authenticate(username=user.username, password=data["password"])
        if user == check_user:
            user.set_password(data["new_password"])
            user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            raise serializers.ValidationError("原密码错误！")

    @action(methods=["patch"], detail=True)
    def reset_password(self, request, *args, **kwargs):
        id = kwargs["pk"]
        data = request.data
        if data["new_password"] != data["pwd_repeat"]:
            raise serializers.ValidationError("新密码和确认密码不一致！")
        if len(data["new_password"]) < 5 or len(data["new_password"]) > 15:
            raise serializers.ValidationError("新密码最少5位，最大14位！")
        user = User.objects.filter(pk=id)[0]
        user.set_password(data["new_password"])
        user.save()
        return Response(status=status.HTTP_200_OK)


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
            '用户名': 'username',
            '客户网名': 'nickname',
            '收件人': 'receiver',
            '地址': 'address',
            '手机': 'mobile',
            '货品编码': 'goods_id',
            '数量': 'quantity',
            '单据类型': 'order_category',
            '机器序列号': 'm_sn',
            '故障部位': 'broken_part',
            '故障描述': 'description',
        }

        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error": []}
        if '.' in _file.name and _file.name.rsplit('.')[-1] in ALLOWED_EXTENSIONS:
            df = pd.read_excel(_file, sheet_name=0, dtype=str)

            FILTER_FIELDS = ["店铺", "客户网名", "收件人", "地址", "手机", "货品编码", "货品名称", "数量", "单据类型",
                             "机器序列号", "故障部位", "故障描述"]

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
            _ret_verify_field = User.verify_mandatory(columns_key)
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
        category_dic = {
            '质量问题': 1,
            '开箱即损': 2,
            '礼品赠品': 3
        }
        report_dic = {"successful": 0, "discard": 0, "false": 0, "repeated": 0, "error":[]}
        jieba.load_userdict("apps/dfc/manualorder/addr_key_words.txt")
        for row in resource:

            order_fields = ["nickname", "receiver", "address", "mobile", "m_sn", "broken_part", "description"]
            order = ManualOrder()
            for field in order_fields:
                setattr(order, field, row[field])
            order.order_category = category_dic.get(row["order_category"], None)
            _q_shop =  Shop.objects.filter(name=row["shop"])
            if _q_shop.exists():
                order.shop = _q_shop[0]
            address = re.sub("[0-9!#$%&\'()*+,-./:;<=>?，。?★、…【】《》？“”‘’！[\\]^_`{|}~\s]+", "", str(order.address))
            seg_list = jieba.lcut(address)

            _spilt_addr = PickOutAdress(seg_list)
            _rt_addr = _spilt_addr.pickout_addr()
            cs_info_fields = ["province", "city", "district", "address"]
            for key_word in cs_info_fields:
                setattr(order, key_word, _rt_addr.get(key_word, None))

            try:
                order.creator = request.user.username
                order.save()
                report_dic["successful"] += 1
            except Exception as e:
                report_dic['error'].append("%s 保存出错" % row["nickname"])
                report_dic["false"] += 1
            goods_details = MOGoods()
            goods_details.manual_order = order
            goods_details.quantity = row["quantity"]
            _q_goods = Goods.objects.filter(goods_id=row["goods_id"])
            if _q_goods.exists():
                goods_details.goods_name = _q_goods[0]
                goods_details.goods_id = row["goods_id"]
            try:
                goods_details.creator = request.user.username
                goods_details.save()
            except Exception as e:
                report_dic['error'].append("%s 保存明细出错" % row["nickname"])
        return report_dic


class DashboardViewset(viewsets.ViewSet, mixins.ListModelMixin):
    permission_classes = (IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        data = {
            "card1": {
                "cck": 2,
                "ccm": 3
            },
            "ppc": "ok"
        }
        return response.Response(data)

