import inspect
import datetime


def logging(obj, name, classlog, content):
    if inspect.isclass(classlog):
        record = classlog()
    else:
        return False
    record.obj = obj
    record.name = name
    record.content = content
    try:
        record.save()
    except Exception as e:
        return False
    return True


def getlogs(obj, classlog):
    ret = []
    if inspect.isclass(classlog):
        r_name = str(classlog.__name__)
    else:
        ret = [{
            "id": -1,
            "name": "捉BUG小达人",
            "content": "读日志函数传的啥玩意！！！（把这个界面整个截图给开发，告诉他，开发的什么玩意！）",
            "created_time": datetime.datetime.now()
        }]
        return ret
    reserver_query_name = "%s_set" % str(r_name).lower()
    try:
        log_details = getattr(obj, reserver_query_name).all().order_by("-id")
    except Exception as e:
        ret = [{
            "id": -1,
            "name": "捉BUG小达人",
            "content": "日志函数传得驴唇不对马嘴啦！！！（把这个界面整个截图给开发，告诉他，开发的什么玩意！）",
            "created_time": datetime.datetime.now()
        }]
        return ret
    for log_detail in log_details:
        data = {
            "id": log_detail.id,
            "name": log_detail.name.username,
            "content": log_detail.content,
            "created_time": '{:%Y-%m-%d %H:%M:%S}'.format(log_detail.created_time)
        }
        ret.append(data)
    return ret


def getfiles(obj, classlog):
    ret = []
    if inspect.isclass(classlog):
        r_name = str(classlog.__name__)
    else:
        ret = [{
            "id": -1,
            "name": "捉BUG小达人",
            "content": "读文件明细函数传的啥玩意！！！（把这个界面整个截图给开发，告诉他，开发的什么玩意！）",
            "created_time": datetime.datetime.now()
        }]
        return ret
    reserver_query_name = "%s_set" % str(r_name).lower()
    try:
        file_details = getattr(obj, reserver_query_name).filter(is_delete=False).order_by("-id")
    except Exception as e:
        ret = [{
            "id": -1,
            "name": "捉BUG小达人",
            "content": "文件明细函数传得驴唇不对马嘴啦！！！（把这个界面整个截图给开发，告诉他，开发的什么玩意！）",
            "created_time": datetime.datetime.now()
        }]
        return ret
    for file_detail in file_details:
        if file_detail.suffix in ['png', 'jpg', 'gif', 'bmp', 'tif', 'svg', 'raw']:
            is_pic = True
        else:
            is_pic = False
        data = {
            "id": file_detail.id,
            "name": file_detail.name,
            "suffix": file_detail.suffix,
            "url": file_detail.url,
            "url_list": [file_detail.url],
            "is_pic": is_pic,
            "creator": file_detail.creator.username,
            "created_time": '{:%Y-%m-%d %H:%M:%S}'.format(file_detail.created_time)
        }
        ret.append(data)
    return ret

