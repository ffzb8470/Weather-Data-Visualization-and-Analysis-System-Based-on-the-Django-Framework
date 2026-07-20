# -*- coding: utf-8 -*-


import os
import sys


def run_pipeline(csv_path=None, spider_args=None):
    """运行完整的数据处理流水线

    参数:
        csv_path: CSV 文件路径（默认自动拼接）
        spider_args: 传递给爬虫的其他参数（字典）
    """
    # ── 1. 路径准备 ──
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
    if csv_path is None:
        csv_path = os.path.join(project_root, 'get_data', 'data', 'raw_aqi_data.csv')  

    print("=" * 60)
    print("  🌐 空气质量数据流水线")
    print("=" * 60)

    # ── 2. 运行爬虫 ──
    print("\n[1/3] 启动爬虫获取数据...")
    sys.path.insert(0, os.path.join(project_root, 'get_data')) 
    try:
        from get_data.weather_spider import WeatherSpider  
        spider = WeatherSpider()  
        result = spider.start(csv_path=csv_path)  
        print(f"  爬虫完成: {result}")
    except Exception as e:
        print(f"  ❌ 爬虫运行失败: {e}")
        print("  请检查网络连接后重试")
        return

    # ── 3. 数据预处理 ──
    print("\n[2/3] 数据预处理（导入 → 去重 → 填补）...")
    try:
        from app01.data_preprocess import run as preprocess_run  
        preprocess_run(csv_path=csv_path)  
    except Exception as e:
        print(f"  ❌ 预处理失败: {e}")
        return

    # ── 4. 数据分析（pandas + numpy） ──
    print("\n[3/3] 数据分析（异常值检测 + 统计摘要）...")
    try:
        from app01.data_analysis import detect_outliers, statistical_summary  

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
        return

    print("\n" + "=" * 60)
    print("  ✅ 流水线全部完成")
    print("=" * 60)


if __name__ == '__main__':
    print("请通过 Django shell 运行: python manage.py shell")
    print(">>> from app01.data_processing_flow import run_pipeline")
    print(">>> run_pipeline()")
