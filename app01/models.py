from django.db import models

class AirQualityRecord(models.Model):  
    """空气质量逐日记录 — 匹配tianqihoubao.com全维度"""
    city = models.CharField(max_length=50, verbose_name='城市', db_index=True)
    date = models.DateField(verbose_name='日期', db_index=True)
    
    # AQI 指数与空气质量等级
    aqi = models.FloatField(verbose_name='AQI指数', null=True, blank=True)
    quality_level = models.CharField(max_length=50, verbose_name='空气质量等级', blank=True, default='')
    
    # 六项污染物
    pm25 = models.FloatField(verbose_name='PM2.5 (μg/m³)', null=True, blank=True)
    pm10 = models.FloatField(verbose_name='PM10 (μg/m³)', null=True, blank=True)
    no2 = models.FloatField(verbose_name='NO2 (μg/m³)', null=True, blank=True)
    so2 = models.FloatField(verbose_name='SO2 (μg/m³)', null=True, blank=True)
    co = models.FloatField(verbose_name='CO (mg/m³)', null=True, blank=True)
    o3 = models.FloatField(verbose_name='O3 (μg/m³)', null=True, blank=True)

    class Meta: 
        verbose_name = '空气质量记录'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['city', 'date']),
        ]
        ordering = ['city', 'date']

    def __str__(self):  
        return f'{self.city} {self.date} AQI={self.aqi} {self.quality_level}'

