#encoding=utf-8
from __future__ import unicode_literals
import sys
sys.path.append("../")

import jieba
import jieba.posseg
import jieba.analyse


seg_list = jieba.cut("我来到北京清华大学", cut_all=True)

seg_list = jieba.cut("我来到北京清华大学", cut_all=False)

seg_list = jieba.cut("他来到了网易杭研大厦")

seg_list = jieba.cut_for_search("小明硕士毕业于中国科学院计算所，后在日本京都大学深造")  # 搜索引擎模式

