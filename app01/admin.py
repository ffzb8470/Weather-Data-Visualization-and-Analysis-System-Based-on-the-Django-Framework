import json
import logging
import os
import sys
from datetime import date

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.shortcuts import render
from django.urls import path

from .models import AirQualityRecord
from .views import get_active_cities



class UserAdmin(BaseUserAdmin):  
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('email',)}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email'),
        }),
    )


admin.site.unregister(User)  
admin.site.register(User, UserAdmin)  


_CRAWL_LIST_FILE = os.path.join(os.path.dirname(__file__), 'crawl_list.json')


def _load_crawl_list():
    """读取持久化的爬取名单，文件不存在时返回默认活跃城市"""
    if os.path.exists(_CRAWL_LIST_FILE):
        try:
            with open(_CRAWL_LIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    return list(get_active_cities()) 


def _save_crawl_list(cities):
    """保存爬取名单到 JSON 文件"""
    os.makedirs(os.path.dirname(_CRAWL_LIST_FILE), exist_ok=True)
    with open(_CRAWL_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)

logger = logging.getLogger(__name__)


def _get_crawl_fn():
    """动态导入爬虫函数（避免启动时依赖未就绪）"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'get_data'))
    from weather_spider import crawl_city_range  
    return crawl_city_range


def _run_crawl(cities):
    """对多个城市爬取去年+今年数据，返回汇总信息"""
    crawl = _get_crawl_fn()
    today = date.today()  
    start = date(today.year - 1, 1, 1)
    end = date(today.year, 12, 31)
    results = []
    for city in cities:
        try:
            saved, skipped, errors, warnings = crawl(city, start, end) 
            results.append({
                'city': city, 'saved': saved, 'skipped': skipped,
                'errors': errors, 'warnings': warnings, 'status': 'ok'
            })
        except Exception as e:
            results.append({
                'city': city, 'saved': 0, 'skipped': 0,
                'errors': [str(e)], 'warnings': [], 'status': 'error'
            })
    return results


def _get_all_candidate_cities():
    """获取所有候选城市：活跃城市 + 数据库中存在的其他城市"""
    all_cities = set(get_active_cities())
    db_cities = AirQualityRecord.objects.values_list('city', flat=True).distinct()  
    return sorted(all_cities)


@admin.register(AirQualityRecord)
class AirQualityRecordAdmin(admin.ModelAdmin): 
    list_display = ('city', 'formatted_date', 'aqi', 'quality_level', 'pm25', 'pm10', 'no2', 'so2', 'co', 'o3')
    list_display_links = ('city', 'formatted_date')
    list_filter = ('city', 'quality_level', 'date')
    search_fields = ('city',)
    list_per_page = 50
    ordering = ('-date', 'city')
    change_list_template = 'admin/airqualityrecord_change_list.html'

    def has_add_permission(self, request):  
        return False

    def formatted_date(self, obj):
        """中文格式日期显示，含星期"""
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        d = obj.date
        return f'{d.year}年{d.month:02d}月{d.day:02d}日 {weekdays[d.weekday()]}'
    formatted_date.short_description = '日期'
    formatted_date.admin_order_field = 'date'

  

    def get_urls(self):  
        urls = super().get_urls()
        custom_urls = [
            path('crawl/', self.admin_site.admin_view(self.crawl_view), name='airqualityrecord-crawl'),  
        ]
        return custom_urls + urls

    def crawl_view(self, request):  
        """爬取管理页面：显示现有名单，可增删城市，点更新后爬取去年+今年数据"""
        results = None
        label = ''
        city_list = []
        existing_cities = sorted(
            AirQualityRecord.objects.values_list('city', flat=True).distinct()
        )

        if request.method == 'POST' and 'save_and_crawl' in request.POST:
            raw = request.POST.get('cities_json', '[]').strip()
            try:
                cities = json.loads(raw)
                if not isinstance(cities, list):
                    raise ValueError
                cities = list(dict.fromkeys(c.strip() for c in cities if c.strip()))
            except (json.JSONDecodeError, ValueError):
                self.message_user(request, '提交数据格式错误', level=messages.WARNING)  
                cities = _load_crawl_list()    
                city_list = cities

            if not cities:
                self.message_user(request, '请至少添加一个城市', level=messages.WARNING)  
                city_list = cities or _load_crawl_list()
            else:
                _save_crawl_list(cities)  
  
                db_cities = set(
                    AirQualityRecord.objects.values_list('city', flat=True).distinct()
                )
                new_cities_set = set(cities)
                cities_to_delete = db_cities - new_cities_set
                deleted_count = 0
                if cities_to_delete:
                    deleted_count, _ = AirQualityRecord.objects.filter(
                        city__in=cities_to_delete
                    ).delete()
           
                results = _run_crawl(cities)  
                label = f'{date.today().year-1}年~{date.today().year}年'
                total_saved = sum(r['saved'] for r in results)
                total_warnings = sorted(set(w for r in results for w in r.get('warnings', [])))
                city_list = cities
                del_msg = f'，已删除 {deleted_count} 条旧城市数据' if deleted_count else ''
                self.message_user(
                    request,
                    f'名单已保存，爬取完成({label})：共保存 {total_saved} 条记录{del_msg}',
                    level=messages.SUCCESS,
                )
        else:
           
            city_list = _load_crawl_list()

        total_saved = sum(r['saved'] for r in results) if results else 0
        total_warnings = sorted(set(w for r in (results or []) for w in r.get('warnings', [])))
        context = dict(
            self.admin_site.each_context(request),
            title='爬取数据管理',
            existing_cities=existing_cities,
            city_list=city_list,
            results=results,
            label=label,
            total_saved=total_saved,
            total_warnings=total_warnings,
            opts=self.model._meta,
            original=self,
        )
        return render(request, 'admin/crawl_page.html', context)
