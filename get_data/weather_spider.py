# -*- coding: utf-8 -*-
"""
天气后报网 AQI 爬虫 — 全维度版本
数据来源: https://www.tianqihoubao.com/aqi/
目标: 爬取 AQI 指数、空气质量等级、PM2.5、PM10、NO2、SO2、CO、O3
"""

import os, sys, re, math, random, csv
from datetime import datetime, timedelta
import urllib.request, urllib.error
from pypinyin import lazy_pinyin

# =============================================
# 城市配置 — 自动拼音转换
# =============================================
# 特殊情况覆盖（如果网站使用非标准拼音 slug）
SLUG_OVERRIDES = {
}

def _name_to_slug(name):
    """中文城市名 → 拼音 slug"""
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    return ''.join(lazy_pinyin(name))

DEFAULT_CITY_NAMES = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '沈阳', '汕头']

CITIES = [{'name': name, 'slug': _name_to_slug(name)} for name in DEFAULT_CITY_NAMES]   # 中文城市名转拼音，用于构建网址（URL）


START_YEAR = 2023
END_YEAR = datetime.now().year


MAX_DELAY_WARN_DAYS = 3


LEVEL_MAP = {
    'excellent': '优',
    'good': '良',
    'lightly_polluted': '轻度污染',
    'moderately_polluted': '中度污染',
    'heavily_polluted': '重度污染',
    'severely_polluted': '严重污染',
    '': '',
}


def level_to_code(raw_level, aqi=None):
    """
    将提取的等级字符串转为英文替代字符保存。
    因为GBK解码可能损坏汉字，所以用模糊匹配+英文代码。
    如果文本匹配失败且有AQI值，则按AQI国标分级作为回退。
    """
    raw = raw_level.strip()

    patterns = [

        ('严重', 'severely_polluted'),
        ('重度', 'heavily_polluted'),
        ('中度', 'moderately_polluted'),
        ('轻度', 'lightly_polluted'),
        ('优', 'excellent'),
        ('良', 'good'),
    ]
    for keyword, code in patterns:
        if keyword in raw:
            return code

    if raw in LEVEL_MAP:
        return raw

    if aqi is not None:
        return level_from_aqi(aqi)
    return 'good' 



def level_from_aqi(aqi):
    if aqi <= 50:
        return 'excellent'
    elif aqi <= 100:
        return 'good'
    elif aqi <= 150:
        return 'lightly_polluted'
    elif aqi <= 200:
        return 'moderately_polluted'
    elif aqi <= 300:
        return 'heavily_polluted'
    else:
        return 'severely_polluted'


def fetch_month_aqi(slug, year, month):
    """爬取某城市某月的数据"""
    url = f'https://www.tianqihoubao.com/aqi/{slug}-{year}{month:02d}.html'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('gbk', errors='replace')   
        return content
    except Exception as e:
        print(f'    [警告] 爬取 {year}年{month}月失败: {e}')
        return None


def parse_full_table(html):
    """
    解析月数据HTML表格，返回 [(date_str, aqi, level, pm25, pm10, no2, so2, co, o3), ...]
    实际表格列: 日期 | AQI 指数 | 质量等级 | 当天 AQI 排名 | PM2.5 | PM10 | No2 | So2 | Co | O3
    clean[0]=日期 [1]=AQI [2]=等级 [3]=排名（跳过） [4]=PM2.5 [5]=PM10 [6]=NO2 [7]=SO2 [8]=CO [9]=O3
    """
    if not html:
        return []
    
    table_start = html.find('<table')
    table_end = html.find('</table>', table_start)
    if table_start < 0 or table_end < 0:
        return []
    
    table_html = html[table_start:table_end + 8]
    

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
    results = []
    
    for row in rows[1:]: 
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        if len(cells) >= 10:

            clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            date_str = clean[0].strip()
            

            if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                continue
            
            try:
                aqi_str = clean[1].strip()
                level_str = clean[2].strip()
                # clean[3] = 当天 AQI 排名
                pm25_str = clean[4].strip()
                pm10_str = clean[5].strip()
                no2_str = clean[6].strip()
                so2_str = clean[7].strip()
                co_str = clean[8].strip()
                o3_str = clean[9].strip()
                

                def to_float(s):
                    s = s.strip()
                    if s in ('', '-', '--', 'None'):
                        return None
                    return float(s)
                
                aqi = to_float(aqi_str)
                pm25 = to_float(pm25_str)
                pm10 = to_float(pm10_str)
                no2 = to_float(no2_str)
                so2 = to_float(so2_str)
                co = to_float(co_str)
                o3 = to_float(o3_str)
                
                results.append((date_str, aqi, level_str, pm25, pm10, no2, so2, co, o3))
            except (ValueError, IndexError):
                continue
    
    return results


# =============================================
# 2. 主流程
# =============================================

class WeatherSpider:
    """爬虫包装类，供编排脚本调用"""

    def start(self, csv_path=None):
        """执行爬取并将数据写入 CSV

        参数:
            csv_path: CSV 文件保存路径（默认: data/raw_aqi_data.csv）
        """
        if csv_path:
            import builtins
            builtins._SPIDER_CSV_PATH = csv_path
        return main()


def _load_existing_records(csv_path):
    """读取已存在的 CSV，返回 (existing_records, by_day, by_month)"""
    existing_records = []
    by_day = set()
    by_month = set()
    if not csv_path or not os.path.exists(csv_path):
        return existing_records, by_day, by_month
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f) 
        for row in reader:
            existing_records.append(row)
            city = row['city']
            date = row['date'] 
            by_day.add((city, date))
            y, m, _ = date.split('-')
            by_month.add((city, int(y), int(m)))
    return existing_records, by_day, by_month


def main(csv_path=None):
    print('=' * 50)
    print('天气后报网 AQI 爬虫 - 全维度版 (增量模式)')
    print(f'数据来源: https://www.tianqihoubao.com/aqi/')
    print(f'城市: {len(CITIES)}个 | 年份: {START_YEAR}-{END_YEAR}')
    print('=' * 50)


    import builtins
    if csv_path is None and hasattr(builtins, '_SPIDER_CSV_PATH'):
        csv_path = builtins._SPIDER_CSV_PATH
    if csv_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
        data_dir = os.path.join(project_root, 'data')
        os.makedirs(data_dir, exist_ok=True)   
        csv_path = os.path.join(data_dir, 'raw_aqi_data.csv')

    existing_records, existing_by_day, existing_by_month = _load_existing_records(csv_path)

    # ============================================
    # 增量爬取：月粒度 + 最新月日粒度
    # ============================================

    all_records = list(existing_records)
    total_days = 0

    years_to_crawl = list(range(START_YEAR, END_YEAR + 1))
    today = datetime.now()

    for year in reversed(years_to_crawl):
        print(f'\n{"="*40}')
        print(f'年度: {year}年')
        print(f'{"="*40}')

        max_month = today.month if year == today.year else 12

        for city in CITIES:
            print(f'\n正在处理: {city["name"]} ({city["slug"]}) - {year}年')
            daily_data = {}

            for m in range(1, max_month + 1):
                #月粒度检查
                is_latest = (year == today.year and m == today.month)
                if not is_latest:
                    has_month = (city['name'], year, m) in existing_by_month
                    if has_month:
                        print(f'  {year}年{m:02d}月: 已有数据，跳过')
                        continue

                print(f'   爬取 {year}年{m:02d}月...', end='')
                html = fetch_month_aqi(city['slug'], year, m)
                if not html:
                    print(' 失败')
                    continue

                month_data = parse_full_table(html)

                #最新月：日粒度过滤
                if is_latest and month_data:
                    prefix = f'{year}-{m:02d}'
                    existing_dates_in_city = {
                        d for (c, d) in existing_by_day
                        if c == city['name'] and d.startswith(prefix)
                    }
                    before = len(month_data)
                    month_data = [ 
                        item for item in month_data
                        if item[0] not in existing_dates_in_city
                    ]
                    print(f' {len(month_data)} 天(新增/共{before}天)')
                else:
                    print(f' {len(month_data)} 天')

                if is_latest and month_data:
                    _latest_date_str = max(item[0] for item in month_data)
                    _latest_date = datetime.strptime(_latest_date_str, '%Y-%m-%d').date()
                    _delay_days = (today.date() - _latest_date).days
                    if _delay_days > MAX_DELAY_WARN_DAYS:
                        print(f'  ⚠ [提醒] 最新数据为 {_latest_date_str}，距今天已 {_delay_days} 天')
                        print(f'     tianqihoubao.com 数据通常延迟 5~10 天，这可能正常。')
                        print(f'     建议过几天再运行爬虫，或者手动确认网站是否已更新。')

                for item in month_data:
                    date_str = item[0]
                    daily_data[date_str] = item[1:]

            if not daily_data:
                print(f'  {city["name"]} {year}年无需更新')
                continue

            print(f'  共获取 {len(daily_data)} 天有效数据')
            total_days += len(daily_data)

            aqi_vals = []
            pm25_vals = []
            pm10_vals = []
            no2_vals = []
            so2_vals = []
            co_vals = []
            o3_vals = []

            for date_str, vals in sorted(daily_data.items()):
                aqi, level, pm25, pm10, no2, so2, co, o3 = vals
                record = {
                    'city': city['name'],
                    'date': datetime.strptime(date_str, '%Y-%m-%d').date().isoformat(),
                    'aqi': aqi,
                    'quality_level': level_to_code(level, aqi=aqi) or '',
                    'pm10': pm10,
                    'no2': no2,
                    'so2': so2,
                    'co': co,
                    'o3': o3,
                }
                all_records.append(record)

                if aqi is not None: aqi_vals.append(aqi)
                if pm25 is not None: pm25_vals.append(pm25)
                if pm10 is not None: pm10_vals.append(pm10)
                if no2 is not None: no2_vals.append(no2)
                if so2 is not None: so2_vals.append(so2)
                if co is not None: co_vals.append(co)
                if o3 is not None: o3_vals.append(o3)

            def avg(lst):
                return round(sum(lst)/len(lst), 1) if lst else 'N/A'
            print(f'  日均值 - AQI:{avg(aqi_vals)} PM2.5:{avg(pm25_vals)} PM10:{avg(pm10_vals)} '
                  f'NO2:{avg(no2_vals)} SO2:{avg(so2_vals)} CO:{avg(co_vals)} O3:{avg(o3_vals)}')
    
    if all_records:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['city', 'date', 'aqi', 'quality_level', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)
        
        cities_in_csv = len(set(r['city'] for r in all_records))
        dates_in_csv = len(set(r['date'] for r in all_records))
        
        print(f'\n完成!')
        print(f'   总记录数: {len(all_records)}')
        print(f'   城市数: {cities_in_csv}')
        print(f'   日期数: {dates_in_csv}')
        print(f'   文件路径: {csv_path}')
        return csv_path
    
    print(f'\n数据采集完毕! 请运行数据预处理将CSV数据导入数据库:')
    print(f'   python manage.py shell')
    print(f'   >>> from app01.data_preprocess import run')
    print(f'   >>> run(csv_path="<csv_path>")')
    return None



# =============================================
# 3. 按城市+时间段爬取并直接写入数据库（供 views 调用）
# =============================================
def get_slug(city_name):
    """根据城市名获取slug — 支持不在预设列表中的城市"""
    for c in CITIES:
        if c['name'] == city_name:
            return c['slug']
    try:
        from pypinyin import lazy_pinyin
        result = ''.join(lazy_pinyin(city_name))
        if result:
            return result
    except Exception:
        pass
    if city_name.isascii():
        return city_name
    return None


def crawl_city_range(city_name, start_date, end_date, progress_callback=None):
    """
    爬取指定城市在日期范围内的数据，直接写入数据库。
    按月粒度跳过已有完整数据的月份。
    返回: (saved_count, skipped_count, errors)
    """
    slug = get_slug(city_name)
    if not slug:
        return 0, 0, [f'未知城市: {city_name}']

    from app01.models import AirQualityRecord
    from datetime import date as date_type
    import calendar

    if isinstance(start_date, str):
        start_date = date_type.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date_type.fromisoformat(end_date)

    saved = 0
    skipped = 0
    errors = []
    warnings = []

    year = start_date.year
    month = start_date.month
    end_year = end_date.year
    end_month = end_date.month

    while (year < end_year) or (year == end_year and month <= end_month):
        if progress_callback:
            progress_callback(city_name, year, month)

        month_start = date_type(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        month_end = date_type(year, month, days_in_month)

        today = date_type.today()
        range_start = max(start_date, month_start)
        range_end = min(end_date, month_end, today)

        if range_start > range_end:
            month += 1
            if month > 12:
                month = 1
                year += 1
            continue

        expected_days = (range_end - range_start).days + 1 

        #月粒度检查
        existing_count = AirQualityRecord.objects.filter(
            date__gte=range_start,
            date__lte=range_end,
        ).count()

        if existing_count >= expected_days:         
            skipped += expected_days
            print(f'  {year}年{month:02d}月: 已有 {existing_count}/{expected_days} 天，跳过')
            month += 1
            if month > 12:
                month = 1
                year += 1
            continue

        html = fetch_month_aqi(slug, year, month)
        if not html:
            errors.append(f'{year}年{month:02d}月 爬取失败')
        else:
            month_data = parse_full_table(html)

            if month_data:
                _latest_date_str = max(item[0] for item in month_data)
                _latest_date = date_type.fromisoformat(_latest_date_str)
                _today = date_type.today()
                _delay_days = (_today - _latest_date).days
                if _delay_days > MAX_DELAY_WARN_DAYS:
                    _msg = (f'最新数据为 {_latest_date_str}，距今天已 {_delay_days} 天。'
                            f'tianqihoubao.com 数据通常延迟 5~10 天，建议过几天再运行爬虫。')
                    warnings.append(_msg)

            existing_dates = set(
                AirQualityRecord.objects.filter(
                    city=city_name,
                    date__gte=range_start,
                    date__lte=range_end,
                ).values_list('date', flat=True)
            )
            for item in month_data:
                date_str, aqi, level, pm25, pm10, no2, so2, co, o3 = item
                rec_date = date_type.fromisoformat(date_str)
                if rec_date < start_date or rec_date > end_date:
                    continue
                if rec_date in existing_dates:
                    skipped += 1
                    continue
                try:
                    AirQualityRecord.objects.create(
                        city=city_name,
                        date=rec_date,
                        aqi=aqi,
                        quality_level=level_to_code(level, aqi=aqi) or '',
                        pm25=pm25,
                        pm10=pm10,
                        no2=no2,
                        so2=so2,
                        co=co,
                        o3=o3,
                    )
                    saved += 1
                except Exception as e:
                    errors.append(f'{date_str} 入库失败: {e}')

        month += 1
        if month > 12:
            month = 1
            year += 1

    return saved, skipped, errors, warnings


if __name__ == '__main__':
    main()