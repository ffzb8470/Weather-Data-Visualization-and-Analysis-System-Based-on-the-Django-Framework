# -*- coding: utf-8 -*-
"""
数据分析模块（只读不写）
功能：异常值检测、数据统计摘要
已重构：使用 pandas + numpy 实现

使用方法：
    python manage.py shell
    >>> from app01.data_analysis import detect_outliers, statistical_summary
    >>> detect_outliers()
    >>> statistical_summary()
"""

import numpy as np
import pandas as pd

# 以下导入需在 Django 环境下运行
try:
    from .models import AirQualityRecord
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    AirQualityRecord = None


def _get_dataframe():
    """将数据库查询结果转为 pandas DataFrame"""
    qs = AirQualityRecord.objects.all().values(
        'id', 'city', 'date', 'aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3'
    )
    df = pd.DataFrame.from_records(qs, index='id')
    df['date'] = pd.to_datetime(df['date'])
    return df


def detect_outliers(method='iqr', multiplier=1.5):
    """异常值检测（只读，不修改数据库）

    method:
        - 'iqr': 四分位距法（默认）
        - 'zscore': Z-Score 法（>3σ视为异常）
    multiplier: IQR 倍数（默认1.5）
    返回：异常值统计字典
    """
    if not DJANGO_AVAILABLE:
        return "Django 环境不可用"

    fields = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    df = _get_dataframe() 
    result = {}

    for f in fields:
        vals = df[f].dropna().values  
        if len(vals) == 0:  
            result[f] = {'count': 0, 'outliers': []}
            continue

        if method == 'iqr':         
            q1 = np.percentile(vals, 25)  
            q3 = np.percentile(vals, 75) 
            iqr = q3 - q1  
            lower = q1 - multiplier * iqr 
            upper = q3 + multiplier * iqr 

        elif method == 'zscore':    
            mean_val = np.mean(vals) 
            std = np.std(vals, ddof=0)  
            lower = mean_val - 3 * std
            upper = mean_val + 3 * std

        else:
            result[f] = {'count': 0, 'error': f'未知方法: {method}'}
            continue


        outlier_mask = (df[f] < lower) | (df[f] > upper) 
        outlier_count = int(outlier_mask.sum())  

        result[f] = {
            'count': outlier_count,
            'lower_bound': round(float(lower), 2),
            'upper_bound': round(float(upper), 2),
            'normal_range': f'[{round(float(lower), 2)}, {round(float(upper), 2)}]',       
        }

    return result 


def statistical_summary():
    """数据统计摘要（只读，不修改数据库）"""
    if not DJANGO_AVAILABLE:
        return "Django 环境不可用"

    fields = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    df = _get_dataframe()

    total_records = len(df)
    cities = df['city'].nunique()
    date_range = f"{df['date'].min().date()} ~ {df['date'].max().date()}"

    summary = {
        '总记录数': total_records,
        '城市数': int(cities),
        '日期范围': date_range,
        '各字段统计': {}
    }

    for f in fields:
        col = df[f].dropna()
        n = len(col)
        if n == 0:
            summary['各字段统计'][f] = {
                '均值': 0, '标准差': 0,
                '最小值': None, '最大值': None,
                '非空记录数': 0,
            }
            continue

        summary['各字段统计'][f] = {
            '均值': round(float(col.mean()), 2),
            '标准差': round(float(col.std(ddof=0)), 2),
            '最小值': float(col.min()) if pd.notna(col.min()) else None,
            '最大值': float(col.max()) if pd.notna(col.max()) else None,
            '非空记录数': n,
        }

    return summary 


if __name__ == '__main__':
    print("请通过 Django shell 运行: python manage.py shell")
    print(">>> from app01.data_analysis import detect_outliers, statistical_summary")
    print(">>> detect_outliers()")
