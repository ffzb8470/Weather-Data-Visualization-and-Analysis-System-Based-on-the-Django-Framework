# -*- coding: utf-8 -*-
"""完整跑一遍项目：清除旧内容 → 执行全部流水线"""

import os, sys

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'untitled.settings')
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import django
django.setup()

from app01.models import AirQualityRecord

# ========== 清除旧内容 ==========
print("=" * 60)
print("  🧹 清除旧内容")
print("=" * 60)

# 1. 删除数据库记录
print("\n[1/4] 清空数据库...")
aqi_count = AirQualityRecord.objects.count()
AirQualityRecord.objects.all().delete()
print(f"  已删除 AirQualityRecord: {aqi_count} 条")

# 2. 删除旧 CSV 文件
print("\n[2/4] 删除旧 CSV 文件...")
import glob
csv_files = glob.glob(os.path.join(project_root, 'get_data', 'data', '*.csv'))
csv_files += glob.glob(os.path.join(project_root, 'data', '*.csv'))
for f in csv_files:
    os.remove(f)
    print(f"  已删除: {f}")
if not csv_files:
    print("  无旧 CSV 文件")

# 3. 确保 data 目录存在
print("\n[3/4] 创建数据目录...")
data_dir = os.path.join(project_root, 'get_data', 'data')
os.makedirs(data_dir, exist_ok=True)
print(f"  已确保目录存在: {data_dir}")

# ========== 执行流水线 ==========
print("\n" + "=" * 60)
print("  🚀 开始执行完整流水线")
print("=" * 60)

csv_path = os.path.join(data_dir, 'raw_aqi_data.csv')
from app01.data_preprocess import run as preprocess_run
from app01.data_analysis import detect_outliers, statistical_summary

# 步骤1: 检查 CSV 是否存在，存在则跳过爬虫
if not os.path.exists(csv_path):
    print("\n[步骤 1/3] CSV 不存在，启动爬虫...")
    from get_data.weather_spider import WeatherSpider
    try:
        spider = WeatherSpider()
        result = spider.start(csv_path=csv_path)
        print(f"  ✅ 爬虫完成: {result}")
    except Exception as e:
        print(f"  ❌ 爬虫失败: {e}")
        print("  流水线终止")
        sys.exit(1)
else:
    filesize = os.path.getsize(csv_path)
    print(f"\n[步骤 1/3] CSV 已存在，跳过爬虫 ({filesize} bytes)")

# 步骤2: 预处理（CSV→DB + 去重 + 插值）
print("\n[步骤 2/3] 数据预处理...")
try:
    preprocess_run(csv_path=csv_path)
except Exception as e:
    print(f"  ❌ 预处理失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 步骤3: 数据分析
print("\n[步骤 3/3] 数据分析...")
try:
    print("\n  ── 异常值检测（IQR法）──")
    outliers = detect_outliers(method='iqr')
    for field, info in outliers.items():
        print(f"    {field}: {info.get('count', 0)} 个异常, "
              f"正常范围: {info.get('normal_range', 'N/A')}")

    print("\n  ── 统计摘要 ──")
    summary = statistical_summary()
    for key, val in summary.items():
        if key == '各字段统计':
            print(f"    {key}:")
            for fname, fstat in val.items():
                print(f"      {fname}: 均值={fstat['均值']}, "
                      f"标准差={fstat['标准差']}, "
                      f"范围=[{fstat['最小值']}, {fstat['最大值']}]")
        else:
            print(f"    {key}: {val}")
except Exception as e:
    print(f"  ❌ 分析失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("  ✅ 全部完成！")
print("=" * 60)
