# coding=utf-8
from django.test import TestCase

# Create your tests here.
import pandas as pd

import jieba
import jieba.posseg as pseg
import jieba.analyse
from collections import defaultdict

# str_add=['山东省青岛市市南区彩虹大道南段1号都江堰市中心商务区（CBD）中国银行(000000)','湖北省武汉市洪山区卓刀泉街道雄楚大道楚康路301号保利拉菲11-2-1104(430070)','北京北京市朝阳区东湖街道慧谷金色家园129号楼6单元502号(000000)','贵州省黔东南苗族侗族自治州凯里市大十字街道丰球豪庭7栋1单元(000000)','内蒙古自治区通辽市奈曼旗大沁他拉镇奈曼旗诺亚方舟东森尼造型二楼(000000)','江苏省徐州市新沂市新安街道馨园雅居9-2-1803(000000)','广东省广州市海珠区南石头街道保利花园保康路9号702(000000)','辽宁省沈阳市浑南区白塔街道创新路233号集美万象2号楼(000000)','广东省佛山市南海区大沥镇黄岐时代水岸二期6栋4503(000000)','广东省佛山市南海区大沥镇岭南路广佛智城A11B塔7楼拓浦精工(000000)','江西省南昌市东湖区凤凰洲管理处庐山南大道197号（南昌燃气昌北营业厅）(330006)','湖北省武汉市洪山区张家湾街道清能清江锦城清江锦城二期十栋1504(430070)']
#
# for str in str_add:
#     seg_list = jieba.cut(str,use_paddle=True, cut_all=False) # 使用paddle模式
#     print("Paddle Mode: " + '/'.join(list(seg_list)))
#     words = pseg.cut(str, use_paddle=True)  # paddle模式
#     words = dict(words)
#     words_reverse = dict(zip(words.values(), words.keys()))
#     print(words)
#     print(words_reverse)
#
#     words_new = defaultdict(list)
#     for key , value in words.items():
#         words_new[value].append(key)
#     print(words_new['ns'])
#     for x, w in jieba.analyse.extract_tags(str, topK=30, withWeight=True):
#         print('%s %s' % (x, w))


with pd.ExcelFile("address.xlsx") as xls:
    df = pd.read_excel(xls, sheet_name=3)
    for row in df["客户地址"]:
        print(row)
        str_address = jieba.cut(row, use_paddle=True, cut_all=False)
        jieba.load_userdict("addr_key_words.txt")
        key_words = pseg.cut(row, use_paddle=True)
        try:
            key_words = dict(key_words)
        except Exception as e:
            print(e)
            continue
        key_words_reverse = zip(key_words.values(), key_words.keys())
        words_new = defaultdict(list)
        for key, value in key_words.items():
            words_new[value].append(key)
        print(str_address)
        print(dict(key_words))
        print(dict(words_new))


        print(key_words_reverse)
        f1 = open("address_result.txt", "a", encoding="utf-8")
        f1.write("%s    %s\n" % (row, words_new["ns"]))
        f1.close()












