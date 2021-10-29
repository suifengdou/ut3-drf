# -*- coding: utf-8 -*-
import oss2
from itertools import islice

# 阿里云账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM用户进行API访问或日常运维，请登录RAM控制台创建RAM用户。
# auth = oss2.Auth('LTAI5tP7rv35wpiRDcVzFJ7t', 'gN18k3NtHlvApFzXqkdfmFiXPhYCE8')
#
#
# # yourEndpoint填写Bucket所在地域对应的Endpoint。以华东1（杭州）为例，Endpoint填写为https://oss-cn-hangzhou.aliyuncs.com。
# endpoint = 'http://oss-cn-beijing.aliyuncs.com'
#
# # 填写Bucket名称。
# bucket = oss2.Bucket(auth, endpoint, 'ut3s1')
#
# for b in islice(oss2.ObjectIterator(bucket), 10):
#     print(b.key)
