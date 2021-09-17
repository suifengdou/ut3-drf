from django.db import models

# Create your models here.
class Nationality(models.Model):
    name = models.CharField(unique=True, max_length=100, verbose_name='国家及地区', help_text='国家及地区')
    abbreviation = models.CharField(unique=True, max_length=3, verbose_name='缩写', help_text='缩写')
    area_code = models.CharField(unique=True, max_length=10, verbose_name='电话区号', help_text='电话区号')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'UTL-G-国家及地区'
        verbose_name_plural = verbose_name
        db_table = 'util_geo_nationality'

    def __str__(self):
        return self.name


class Province(models.Model):
    nationality = models.ForeignKey(Nationality, on_delete=models.CASCADE, verbose_name='国家', help_text='国家')
    name = models.CharField(unique=True, max_length=150, verbose_name="省份", help_text='省份')
    area_code = models.CharField(unique=True, max_length=10, verbose_name='电话区号', help_text='电话区号')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'UTL-G-省份'
        verbose_name_plural = verbose_name
        db_table = 'util_geo_province'

    def __str__(self):
        return self.name


class City(models.Model):
    nationality = models.ForeignKey(Nationality, on_delete=models.CASCADE, verbose_name='国家', help_text='国家')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省份', help_text='省份')
    name = models.CharField(unique=True, max_length=100, verbose_name='城市', help_text='城市')
    area_code = models.CharField(max_length=10, verbose_name='电话区号', help_text='电话区号')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'UTL-G-城市'
        verbose_name_plural = verbose_name
        db_table = 'util_geo_city'

    def __str__(self):
        return self.name


class District(models.Model):
    nationality = models.ForeignKey(Nationality, on_delete=models.CASCADE, verbose_name='国家', help_text='国家')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, verbose_name='省份', help_text='省份')
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='城市', help_text='城市')
    name = models.CharField(max_length=100, db_index=True, verbose_name='区县', help_text='区县')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记', help_text='删除标记')
    creator = models.CharField(null=True, blank=True, max_length=150, verbose_name='创建者', help_text='创建者')

    class Meta:
        verbose_name = 'UTL-G-区县'
        verbose_name_plural = verbose_name
        db_table = 'util_geo_district'

    def __str__(self):
        return self.name