# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import AirQualityRecord
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta
import json, os

# ─── 城市名单动态化 ──────────────────────────────

_CRAWL_LIST_FILE = os.path.join(os.path.dirname(__file__), 'crawl_list.json')


_COLOR_PALETTE = [
    '#e8634a', '#4a90d9', '#7bc67e', '#f5a623', '#9b59b6',
    '#1abc9c', '#e67e22', '#34495e', '#c0392b', '#2ecc71',
    '#3498db', '#e74c3c', '#f39c12', '#8e44ad', '#16a085',
    '#d35400', '#27ae60', '#2980b9', '#7f8c8d', '#2c3e50',
]


def _load_crawl_list():
    """读取持久化的爬取名单，文件不存在时从数据库获取"""
    if os.path.exists(_CRAWL_LIST_FILE):
        try:
            with open(_CRAWL_LIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f) 
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
   
    db_cities = AirQualityRecord.objects.values_list('city', flat=True).distinct() 
    return sorted(db_cities) if db_cities else []


def get_active_cities():
    """获取活跃城市列表：爬取名单 + 数据库中存在的其他城市（去重排序）"""
    cities = set(_load_crawl_list())
    db_cities = AirQualityRecord.objects.values_list('city', flat=True).distinct()
    cities.update(db_cities)  
    return sorted(cities)


def get_city_colors(cities=None):
    """为城市列表动态分配颜色"""
    if cities is None:
        cities = get_active_cities()
    palette = _COLOR_PALETTE
    return {city: palette[i % len(palette)] for i, city in enumerate(cities)}

# 所有污染物维度
POLLUTANT_FIELDS = ['aqi', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3']
POLLUTANT_NAMES = {
    'aqi': 'AQI指数', 'pm25': 'PM2.5 (μg/m³)', 'pm10': 'PM10 (μg/m³)',
    'no2': 'NO2 (μg/m³)', 'so2': 'SO2 (μg/m³)', 'co': 'CO (mg/m³)', 'o3': 'O3 (μg/m³)'
}
POLLUTANT_UNITS = {
    'aqi': '', 'pm25': 'μg/m³', 'pm10': 'μg/m³',
    'no2': 'μg/m³', 'so2': 'μg/m³', 'co': 'mg/m³', 'o3': 'μg/m³'
}

# 英→中等级映射
LEVEL_DISPLAY = {
    'excellent': '优',
    'good': '良',
    'lightly_polluted': '轻度污染',
    'moderately_polluted': '中度污染',
    'heavily_polluted': '重度污染',
    'severely_polluted': '严重污染',
}


def login(request):
    """登录页：POST 验证用户名密码，通过后跳转到首页"""
    if request.method == 'POST':
        username = request.POST.get('user')
        pwd = request.POST.get('pwd')
        user = auth.authenticate(username=username, password=pwd)  
        if user:
            auth.login(request, user) 
            return redirect('/index/')
        return render(request, 'login.html', {'error': '用户名或密码错误'})
    return render(request, 'login.html')

def logout(request):
    """登出后跳转到登录页"""
    auth.logout(request)
    return redirect('/login/')

def reg(request):
    """注册页：POST 创建新用户后跳转到登录页"""
    if request.method == 'POST':
        user = request.POST.get('user')
        pwd = request.POST.get('pwd')
        User.objects.create_user(username=user, password=pwd)
        return redirect('/login/')
    return render(request, 'reg.html')


# =============================================
# 工具函数
# =============================================

def city_colors():
    """生成 [(城市, 颜色), ...] 列表，供模板遍历使用"""
    cities = get_active_cities()
    colors = get_city_colors(cities) 
    return [(c, colors.get(c, '#37A2DA')) for c in cities]


def get_data_range():
    """获取数据库中数据的时间范围"""
    latest = AirQualityRecord.objects.order_by('-date').first()
    oldest = AirQualityRecord.objects.order_by('date').first()
    return {
        'data_latest_date': latest.date if latest else None,
        'data_oldest_date': oldest.date if oldest else None,
    }




@login_required
def daily_trend(request):
    """近30天逐日AQI、PM2.5、PM10趋势"""
   
    dr = get_data_range() 
    latest_date = dr.get('data_latest_date')

   
    if latest_date:
        thirty_days_ago = latest_date - timedelta(days=30)
    else:
        thirty_days_ago = datetime.now() - timedelta(days=30)
    records = AirQualityRecord.objects.filter(date__gte=thirty_days_ago).order_by('date') 

    cities = get_active_cities()
    colors = get_city_colors(cities)

    data_raw = {city: [] for city in cities}
    date_set = set()

    for r in records:
        date_str = r.date.strftime('%m-%d')
        date_set.add(date_str)
        if r.city not in data_raw:
            continue  
        data_raw[r.city].append({
            'date': date_str,
            'aqi': r.aqi or 0,
            'pm25': r.pm25 or 0,
            'pm10': r.pm10 or 0,
        })

    dates = sorted(date_set)

    return render(request, 'daily_trend.html', {
        'active_page': 'daily_trend',
        'dates': json.dumps(dates),
        'data_raw': json.dumps(data_raw),
        'cities': json.dumps(cities),
        'colors': json.dumps(colors),
        **dr,
    })


# =============================================
# level_distribution: 空气质量等级分布饼图
# =============================================
def _get_level_index(level_str, level_display):
    """将等级字符串转为索引（0=优, 1=良, 2=轻度, 3=中度, 4=重度, 5=严重）"""
    cn = level_display.get(level_str, level_str)
    if '优' in cn:
        return 0
    elif '轻度' in cn:
        return 2
    elif '中度' in cn:
        return 3
    elif '重度' in cn:
        return 4
    elif '严重' in cn:
        return 5
    else:
        return 1  # 良

@login_required
def level_distribution(request):
    """各城市空气质量等级分布（饼图），支持年份和城市筛选"""
    LEVELS = ['优', '良', '轻度污染', '中度污染', '重度污染', '严重污染']
    LEVEL_DISPLAY = {
        'excellent': '优', 'good': '良',
        'lightly_polluted': '轻度污染', 'moderately_polluted': '中度污染',
        'heavily_polluted': '重度污染', 'severely_polluted': '严重污染',
    }
    
    cities = get_active_cities()
    colors = get_city_colors(cities)

    selected_year = request.GET.get('year')
    selected_city = request.GET.get('city', '').strip()
    if not selected_city:
        selected_city = cities[0]

    all_years = AirQualityRecord.objects.dates('date', 'year', order='DESC')
    available_years = [d.year for d in all_years]
    if not available_years:
        available_years = [datetime.now().year]

    try:
        selected_year = int(request.GET.get('year', ''))
    except (ValueError, TypeError):
        selected_year = None

    if not selected_year or selected_year not in available_years:
        selected_year = available_years[0]

    yearly_data = {}
    for year in available_years:
        yearly_data[year] = {city: [0] * 6 for city in cities}

    for r in AirQualityRecord.objects.all().iterator():
        year = r.date.year
        if year not in yearly_data:
            continue
        city_data = yearly_data[year].get(r.city)
        if city_data is None:
            continue  
        idx = _get_level_index((r.quality_level or '').strip(), LEVEL_DISPLAY)
        city_data[idx] += 1

    city_level_data = {}
    for city in cities:
        city_level_data[city] = yearly_data[selected_year].get(city, [0]*6)

    dr = get_data_range()
    return render(request, 'level_distribution.html', {
        'active_page': 'level_distribution',
        'cities': cities,
        'selected_city': selected_city,
        'colors': colors,
        'levels': LEVELS,
        'level_data': json.dumps(city_level_data),
        'yearly_data': json.dumps(yearly_data),
        'available_years': available_years,
        'selected_year': selected_year,
        **dr,
    })


# =============================================
# index: 首页 — 城市卡片
# =============================================
@login_required
def index(request):
    """城市卡片：展示各城市最新空气质量数据"""
    from django.db.models import Subquery, OuterRef
    latest_ids = (
        AirQualityRecord.objects.values('city')
        .annotate(max_id=Subquery(
            AirQualityRecord.objects.filter(city=OuterRef('city'))
            .order_by('-date', '-id').values('id')[:1]
        ))
        .values('max_id')
    )
    latest_records = AirQualityRecord.objects.filter(id__in=Subquery(latest_ids))
    latest_data = {r.city: r for r in latest_records} 

    all_dates = [r.date for r in latest_records if r.date] 
    if all_dates:
        latest_date = max(all_dates)
        day_start = latest_date - timedelta(days=29)
        records_30d = AirQualityRecord.objects.filter(date__gte=day_start).order_by('date')
    else:
        records_30d = AirQualityRecord.objects.none()

    cities = get_active_cities()
    colors = get_city_colors(cities)
    
    daily_data = {}
    for city in cities:
        daily_data[city] = {}
    for r in records_30d:
        ds = r.date.strftime('%m-%d')
        daily_data[r.city][ds] = {
            'aqi': r.aqi or 0,
            'pm25': r.pm25 or 0,
            'pm10': r.pm10 or 0,
        }

    latest_json = {}
    for city, rec in latest_data.items():
        latest_json[city] = {
            'date': rec.date.strftime('%Y-%m-%d'),
            'aqi': rec.aqi,
            'pm25': rec.pm25,
            'pm10': rec.pm10,
            'no2': rec.no2,
            'so2': rec.so2,
            'co': rec.co,
            'o3': rec.o3,
            'quality_level': LEVEL_DISPLAY.get(rec.quality_level, ''),
        }

    dr = get_data_range()
    return render(request, 'index.html', {
        'active_page': 'index',
        'cities': cities,
        'cities_list': cities,
        'colors': colors,
        'latest_data': latest_data,
        'latest_json': json.dumps(latest_json),
        'daily_data': json.dumps(daily_data),
        'pollutant_names': POLLUTANT_NAMES,
        **dr,
    })


# =============================================
# compare: 多城市多指标对比
# =============================================
@login_required
def compare(request):
    """对比页：用户选择城市和指标，生成对比图表"""
    raw_cities = request.GET.getlist('cities')
    selected_cities = []
    for c in raw_cities:
        selected_cities.extend([x.strip() for x in c.split(',') if x.strip()])
    if not selected_cities:
        selected_cities = get_active_cities()[:3]
    selected_field = request.GET.get('field', 'aqi')

    latest_record = AirQualityRecord.objects.order_by('-date').first()
    if latest_record:
        months_ago_12 = latest_record.date - timedelta(days=365)
    else:
        months_ago_12 = datetime.now() - timedelta(days=365)
    data = {}
    for city in get_active_cities():
        records = AirQualityRecord.objects.filter(
            city=city, date__gte=months_ago_12
        ).order_by('date')
        city_data = {}
        for r in records:
            date_str = r.date.strftime('%Y-%m-%d')
            city_data[date_str] = {
                'aqi': r.aqi, 'pm25': r.pm25, 'pm10': r.pm10,
                'no2': r.no2, 'so2': r.so2, 'co': r.co, 'o3': r.o3,
            }
        data[city] = city_data

    dr = get_data_range()
    colors_dict = get_city_colors(get_active_cities())
    return render(request, 'compare.html', {
        'active_page': 'compare',
        'cities': get_active_cities(),
        'colors_json': json.dumps(colors_dict),
        'selected_cities': selected_cities,
        'selected_field': selected_field,
        'data': json.dumps(data),
        'pollutant_fields': POLLUTANT_FIELDS,
        'pollutant_names': POLLUTANT_NAMES,
        'field_label': POLLUTANT_NAMES.get(selected_field, selected_field),
        **dr,
    })

