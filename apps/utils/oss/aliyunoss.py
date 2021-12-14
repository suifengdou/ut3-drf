# coding: utf-8

import oss2
import datetime
import re
from ut3.settings import OSS_CONFIG
from itertools import islice
import hashlib


class AliyunOSS(object):

    def __init__(self, prefix, files):
        self.AccessKeyId = OSS_CONFIG["AccessKeyId"]
        self.AccessKeySecret = OSS_CONFIG["AccessKeySecret"]
        self.endpoint = OSS_CONFIG["endpoint"]
        self.bucket_name = OSS_CONFIG["bucket_name"]
        self.files = files
        self.prefix = prefix
        self.urls = []
        self.errors = {}

    def upload(self, *args, **kwargs):
        auth = oss2.Auth(self.AccessKeyId, self.AccessKeySecret)
        bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        for file in self.files:
            object_name = self.create_object_name(file)
            try:
                result = bucket.put_object(object_name, file)
                self.urls.append({ "name": file.name, "url": result.resp.response.url })
            except Exception as e:
                self.errors["上传失败"] = "%s 上传失败" % str(file.name)
        result_urls = {
            "urls": self.urls,
            "error": self.errors
        }
        return result_urls


    def create_object_name(self, file):
        c_time = datetime.datetime.now()
        file_name, suffix = str(file.name).split(".")
        serial_number = re.sub("[- .:]", "", str(c_time))
        file_name = str(hashlib.md5(file_name.encode(encoding='UTF-8')).hexdigest())
        file_name = '%s%s' % (file_name, serial_number[:10])
        object_name = '%s/%s/%s/%s/%s.%s' % (self.prefix, c_time.year, c_time.month, c_time.day, file_name, suffix)
        return object_name