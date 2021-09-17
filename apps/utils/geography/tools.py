# coding: utf8
from .models import Nationality, Province, City, District
from functools import reduce


class PickOutAdress():

    def __init__(self, addr_list):
        self.addr_list = addr_list
        self.province = None
        self.city = None
        self.district = None
        self.address = None
        self.switch = True
        self.addr_index = 0
        self.special_city = ['仙桃市', '天门市', '神农架林区', '潜江市', '济源市', '五家渠市', '图木舒克市', '铁门关市',
                             '石河子市', '阿拉尔市', '嘉峪关市', '五指山市', '文昌市', '万宁市', '屯昌县', '三亚市', '三沙市',
                             '琼中黎族苗族自治县', '琼海市', '陵水黎族自治县', '临高县', '乐东黎族自治县', '东方市', '定安县',
                             '儋州市', '澄迈县', '昌江黎族自治县', '保亭黎族苗族自治县', '白沙黎族自治县', '中山市', '东莞市']
        self.terminator = 0


    def pickout_addr(self, *args, **kwargs):
        index = 0
        for words in self.addr_list:
            if self.terminator:
                break
            if not self.province:
                self.pickout_province(words, index)
            if not self.city:
                self.pickout_city(words, index)
            if not self.district:
                self.pickout_district(words, index)
            index += 1
        if self.city not in self.special_city and not self.district:
            _q_district_again = District.objects.filter(city=self.city, name__contains="其他区")
            if _q_district_again.exists():
                self.district = _q_district_again[0]
        self.address = reduce(lambda x, y: str(x) + str(y), self.addr_list[self.addr_index:])
        result_addr = {
            "province": self.province,
            "city": self.city,
            "district": self.district,
            "address": self.address
        }
        return result_addr

    def pickout_province(self, words, index, *args, **kwargs):
        _q_province = Province.objects.filter(name__icontains=words)
        if _q_province.exists():
            self.province = _q_province[0]
            if self.switch:
                self.switch = False
                self.addr_index = index
        else:
            _q_province_again = Province.objects.filter(name__icontains=words[:2])
            if _q_province_again.exists():
                self.province = _q_province_again[0]
                if self.switch:
                    self.switch = False
                    self.addr_index = index


    def pickout_city(self, words, index, *args, **kwargs):
        if self.province:
            _q_city = City.objects.filter(province=self.province, name__icontains=words)
            if _q_city.exists():
                self.city = _q_city[0]
                if self.switch:
                    self.switch = False
                    self.addr_index = index
        else:
            _q_city = City.objects.filter(name=words)
            if _q_city.exists():
                self.city = _q_city[0]
                if not self.province:
                    self.province = self.city.province
                if self.switch:
                    self.switch = False
                    self.addr_index = index
            else:
                _q_city_again = City.objects.filter(name__icontains=words[:2])
                if _q_city_again.exists():
                    self.city = _q_city[0]
                    if not self.province:
                        self.province = self.city.province
                    if self.switch:
                        self.switch = False
                        self.addr_index = index

    def pickout_district(self, words, index, *args, **kwargs):
        if self.province and not self.city:
            _q_district_direct = District.objects.filter(province=self.province, name__contains=words)
            if _q_district_direct.exists():
                self.district = _q_district_direct[0]
                self.city = self.district.city
                self.terminator = 1
        if self.city:
            if self.city.name in self.special_city:
                self.terminator = 1
            _q_district = District.objects.filter(city=self.city, name__contains=words)
            if _q_district.exists():
                self.district = _q_district[0]
                self.terminator = 1


