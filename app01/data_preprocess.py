# -*- coding: utf-8 -*-
"""
数据预处理模块（执行型 — 会修改数据库）
功能：数据去重、缺失值处理
已重构：使用 pandas + numpy 实现

使用方法：
    python manage.py shell
    >>> from app01.data_preprocess import run
    >>> run()
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


def remove_duplicates():
    """去重：按城市+日期去重，保留最新一条（使用 pandas 检测）"""
    if not DJANGO_AVAILABLE:
        return "Django 环境不可用"

   
    qs = AirQualityRecord.objects.values('id', 'city', 'date')  
    df = pd.DataFrame.from_records(qs)  

   
    dup_mask = df.duplicated(subset=['city', 'date'], keep='last')  
    dup_ids = df.loc[dup_mask, 'id'].tolist()  

    if not dup_ids:
        return "去重完成，共删除 0 条重复记录"

    # 批量删除
    deleted, _ = AirQualityRecord.objects.filter(id__in=dup_ids).delete()  
    return f"去重完成，共删除 {deleted} 条重复记录"


def fill_missing_values(method='interpolate'):
    """缺失值处理（使用 pandas + numpy）

    method:
        - 'interpolate': 线性插值（按城市分组，按日期排序后填补）
        - 'mean': 用该城市的平均值填充
        - 'drop': 删除含缺失值的记录
    """
    if not DJANGO_AVAILABLE:
        return "Django 环境不可用"

    fields = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']

    if method == 'drop':
        
        q = {}
        for f in fields:
            q[f'{f}__isnull'] = True  
        records = AirQualityRecord.objects.filter(**q)  
        deleted = records.count()  
        records.delete()  
        return f"已删除 {deleted} 条含缺失值的记录"

   
    qs = AirQualityRecord.objects.all().values(
        'id', 'city', 'date', *fields
    )  
    df = pd.DataFrame.from_records(qs) 
    df['date'] = pd.to_datetime(df['date'])  

    updated_count = 0

    for city in df['city'].unique():
        city_mask = df['city'] == city
        city_df = df.loc[city_mask].sort_values('date').copy()  

        for f in fields:
            null_mask = city_df[f].isna() 
            if null_mask.sum() == 0:
                continue

            if method == 'interpolate':
                
                city_df[f] = city_df[f].interpolate(method='linear', limit_direction='both')  
                mean_val = city_df[f].mean()  
                city_df[f] = city_df[f].fillna(mean_val) 
            else:
                return "未知方法"

            # 更新数据库
            for _, row in city_df.loc[null_mask].iterrows(): 
                if pd.notna(row[f]):  
                    updated_count += 1
                    AirQualityRecord.objects.filter(id=row['id']).update(**{f: round(row[f], 1)})  

    if method == 'interpolate':
        return f"线性插值完成，共填充 {updated_count} 个缺失值"
    elif method == 'mean':
        return f"均值填充完成，共填充 {updated_count} 个缺失值"


def import_csv(csv_path):
    """从CSV文件导入数据到数据库（使用 pandas 读取）"""
    if not DJANGO_AVAILABLE:
        print("错误：请在 Django 环境下运行 (python manage.py shell)")
        return

    print(f'正在从CSV导入数据: {csv_path}')

  
    df = pd.read_csv(csv_path, encoding='utf-8')  
    print(f'  CSV 读取完成: {len(df)} 行, 列: {list(df.columns)}')

   
    df.columns = df.columns.str.strip()

  
    required_cols = ['city', 'date']
    for col in required_cols:
        if col not in df.columns:
            print(f'  错误：CSV 缺少必需列 "{col}"')
            return

    
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date  

    
    numeric_cols = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')  
        else:
            df[col] = None

    
    if 'quality_level' not in df.columns:
        df['quality_level'] = ''

    
    records = []
    for _, row in df.iterrows():
        record = AirQualityRecord(
            city=str(row['city']).strip(),
            date=row['date'],
            aqi=float(row['aqi']) if pd.notna(row['aqi']) else None,
            quality_level=str(row['quality_level']) if pd.notna(row['quality_level']) else '',
            pm25=float(row['pm25']) if pd.notna(row['pm25']) else None,
            pm10=float(row['pm10']) if pd.notna(row['pm10']) else None,
            no2=float(row['no2']) if pd.notna(row['no2']) else None,
            so2=float(row['so2']) if pd.notna(row['so2']) else None,
            co=float(row['co']) if pd.notna(row['co']) else None,
            o3=float(row['o3']) if pd.notna(row['o3']) else None,
        )
        records.append(record)

    AirQualityRecord.objects.bulk_create(records, batch_size=500)  
    print(f'成功导入 {len(records)} 条记录到数据库')


def run(csv_path=None):
    """一键运行完整预处理流程

    参数:
        csv_path: CSV文件路径，提供则先导入数据到数据库
    """
    if not DJANGO_AVAILABLE:
        print("错误：请在 Django 环境下运行 (python manage.py shell)")
        return

    
    from app01.data_analysis import detect_outliers, statistical_summary  

    print("=" * 60)
    print("  流程开始")
    print("=" * 60)

   
    step = 1
    if csv_path:
        print(f"\n[1] 从CSV导入数据...")
        import_csv(csv_path)  
        step = 2

   
    print(f"\n[{step}/4] 数据去重...")
    step += 1
    result = remove_duplicates() 
    print(f"  {result}")

    print(f"\n[{step}/4] 缺失值处理（线性插值）...")
    step += 1
    result = fill_missing_values(method='interpolate')  
    print(f"  {result}")

    
    print(f"\n[{step}/4] 异常值检测（IQR法）...")
    step += 1
    outliers = detect_outliers(method='iqr')  
    for field, info in outliers.items():
        print(f"  {field}: {info.get('count', 0)} 个异常值, "
              f"正常范围: {info.get('normal_range', 'N/A')}")

    print(f"\n[{step}/4] 数据统计摘要:")
    step += 1
    summary = statistical_summary()  
    for key, val in summary.items():
        if key != '各字段统计':
            print(f"  {key}: {val}")
    print("  各字段统计:")
    for field, stats in summary.get('各字段统计', {}).items():
        print(f"    {field}: 均值={stats['均值']}, "
              f"标准差={stats['标准差']}, "
              f"范围=[{stats['最小值']}, {stats['最大值']}]")

    print("\n" + "=" * 60)
    print("  流程完成")
    print("=" * 60)


if __name__ == '__main__':
    print("请通过 Django shell 运行: python manage.py shell")
    print(">>> from app01.data_preprocess import run")
    print(">>> run()")
