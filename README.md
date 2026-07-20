# 🌬️ 城市空气质量数据分析可视化系统

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![Pandas](https://img.shields.io/badge/Pandas-2.3-orange)
![NumPy](https://img.shields.io/badge/NumPy-2.3-blue)
![ECharts](https://img.shields.io/badge/ECharts-5-red)
![Bootstrap](https://img.shields.io/badge/Bootstrap-4.6-purple)

> 基于 Django + Pandas/NumPy + ECharts 的多维度空气质量数据可视化平台。  
> 覆盖 **爬虫采集 → Pandas 清洗 → NumPy 统计分析 → ECharts 可视化** 全流程。

---

## 📋 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Django 4.2 (Python) |
| **数据库** | SQLite（开发默认）↔ MySQL（生产通过 settings_local.py 切换） |
| **数据爬虫** | urllib + 正则解析 |
| **数据处理** | **Pandas**（CSV 读写、去重、缺失值插值） |
| **数据分析** | **NumPy**（百分位数、均值、标准差、异常检测） |
| **后台管理** | SimpleUI（基于 Django Admin） |
| **前端模板** | Django Template Language |
| **UI 框架** | Bootstrap 4.6 + Font Awesome 6 |
| **图表引擎** | ECharts 5 (CDN) |
| **主题系统** | CSS 变量 + localStorage 持久化（亮/暗色） |

---

## 🏗️ 项目架构

```
├── manage.py                          # Django 项目入口
├── requirements.txt                   # 项目依赖
├── run_all.py                         # 一键全流程流水线（爬取→清洗→分析）
│
├── untitled/                          # Django 项目配置
│   ├── __init__.py
│   ├── settings.py                    # 全局配置
│   ├── settings_local.example.py      # MySQL 配置模板（复制为 settings_local.py 即可切换）
│   ├── urls.py                        # URL 路由（含所有路由）
│   ├── wsgi.py
│   └── asgi.py
│
├── app01/                             # 核心应用
│   ├── models.py                      # 数据模型（AirQualityRecord）
│   ├── views.py                       # 视图函数（登录、仪表盘、对比等）
│   ├── data_processing_flow.py        # 数据流水线编排（run_pipeline）
│   ├── data_preprocess.py             # 数据清洗（pandas 去重、插值）
│   ├── data_analysis.py               # 数据分析（numpy 统计摘要、异常检测）
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── custom_filters.py          # 自定义模板过滤器
│   ├── apps.py
│   └── admin.py
│
├── get_data/                          # 数据采集模块
│   ├── weather_spider.py              # 天气后报网 AQI 爬虫
│   └── data/
│       └── raw_aqi_data.csv           # 爬取的原始数据（运行时生成）
│
├── templates/                         # 前端模板
│   ├── base.html                      # 基础布局（侧栏 + 亮/暗主题）
│   ├── index.html                     # 首页仪表盘
│   ├── daily_trend.html               # AQI 日趋势图
│   ├── level_distribution.html        # 空气质量等级分布
│   ├── compare.html                   # 多城市对比
│   ├── login.html                     # 用户登录
│   └── reg.html                       # 用户注册
│
├── static/                            # 静态资源
│   └── css/
│       ├── base.css                   # 基础样式（主题变量、布局）
│       ├── auth.css                   # 登录/注册页面样式
│       ├── index.css                  # 仪表盘样式
│       ├── compare.css                # 对比页面样式
│       ├── daily_trend.css            # 日趋势页面样式
│       └── level_distribution.css     # 等级分布页面样式
│
└── db.sqlite3                         # 数据库文件（运行时生成）
```

---

## 🎯 功能特性

### 数据采集
- 爬虫目标：[天气后报网](https://www.tianqihoubao.com/aqi/)
- 覆盖 **8 个城市**：北京、上海、广州、成都、沈阳、武汉、拉萨、兰州
- 时间跨度：**2023 年 ~ 当前年份**（逐年逐月爬取）
- 监测指标：AQI、PM2.5、PM10、NO₂、SO₂、CO、O₃
- 增量爬取：已有数据自动跳过，只补充缺失月份

### 数据预处理（Pandas）

| 步骤 | 方法 | 说明 |
|------|------|------|
| CSV 导入 | `pandas.read_csv` | 从 CSV 批量导入至数据库 |
| 去重 | `pandas.DataFrame.duplicated` | 按城市 + 日期去重，保留首条 |
| 缺失值填充 | `pandas.DataFrame.interpolate` + `fillna` | 线性插值，剩余用均值填充 |

### 数据分析（NumPy）

| 功能 | 方法 | 输出 |
|------|------|------|
| 统计摘要 | `numpy.mean` / `std` / `min` / `max` | 各字段均值、标准差、范围 |
| 异常值检测（IQR） | `numpy.percentile` + 四分位距 | 每字段异常值数量 + 正常范围 |
| 异常值检测（Z-Score） | `numpy.mean` / `std` + Z 阈值 | 每字段异常值数量 + Z 阈值 |

### 可视化展示

| 页面 | 路由 | 功能 |
|------|------|------|
| 仪表盘 | `/` | 城市卡片网格，点击展开近 30 天趋势 + 污染物饼图 |
| 日趋势 | `/daily_trend/` | 选定城市近 30 天 AQI 折线图 |
| 等级分布 | `/level_distribution/` | 空气质量等级（优/良/轻污等）占比柱状图 |
| 城市对比 | `/compare/` | 多城市多污染物对比折线图 |

### 系统特性
- ✅ 用户注册 / 登录 / 登出
- ✅ 亮色 / 暗色主题切换（CSS 变量 + localStorage 持久化）
- ✅ 响应式布局（侧栏 + 自适应内容区）
- ✅ 回到顶部按钮
- ✅ SimpleUI 后台管理（`/admin/`）

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 3. 一键运行完整数据流水线（爬取 → 清洗 → 分析）
python run_all.py

# 4. 启动开发服务器
python manage.py runserver
```

浏览器访问 `http://127.0.0.1:8000`，注册账号后即可使用。

后台管理：`http://127.0.0.1:8000/admin/`

### 🔁 切换至 MySQL（生产环境）

```bash
# 1. 复制配置模板
cp untitled/settings_local.example.py untitled/settings_local.py

# 2. 编辑 settings_local.py，修改数据库连接信息
#    （数据库需提前创建，字符集 utf8mb4）
# 3. 安装 MySQL 客户端
pip install pymysql

# 4. 重新迁移
python manage.py migrate
```

> 系统检测到 `settings_local.py` 存在时自动使用 MySQL，删除该文件即可回退 SQLite。

---

## 📦 依赖清单

```
Django>=4.2,<5.0       # Web 框架
pymysql>=1.0.0          # MySQL 驱动（可选，当前使用 SQLite）
simpleui>=2022.0.0      # 后台管理主题
pandas>=2.0.0           # 数据清洗（CSV 读写、去重、插值）
numpy>=1.24.0           # 数据分析（统计计算、异常检测）
```

---

## 🔧 独立模块使用

### 一键全流程（推荐）

```bash
python run_all.py
```

依次执行：清空旧数据 → 爬虫采集 → Pandas 清洗 → NumPy 分析 → 输出摘要。

### 单独爬取数据

```python
from get_data.weather_spider import WeatherSpider
spider = WeatherSpider()
csv_path = spider.start()  # 返回 CSV 文件路径
```

### 单独进行数据清洗

```python
from app01.data_preprocess import run
run(csv_path="get_data/data/raw_aqi_data.csv")
```

### 单独进行数据分析

```python
from app01.data_analysis import detect_outliers, statistical_summary
detect_outliers(method='iqr')          # 异常值检测（IQR 法）
detect_outliers(method='zscore')       # 异常值检测（Z-Score 法）
statistical_summary()                  # 统计摘要
```

### 流水线编排

```python
from app01.data_processing_flow import run_pipeline
run_pipeline()
```

---

## 📊 数据模型

### `AirQualityRecord` — 空气质量逐日记录

| 字段 | 类型 | 说明 |
|------|------|------|
| city | CharField | 城市名，带索引 |
| date | DateField | 日期，带索引 |
| aqi | FloatField | AQI 指数 |
| quality_level | CharField | 空气质量等级 |
| pm25 | FloatField | PM2.5 (μg/m³) |
| pm10 | FloatField | PM10 (μg/m³) |
| no2 | FloatField | NO₂ (μg/m³) |
| so2 | FloatField | SO₂ (μg/m³) |
| co | FloatField | CO (mg/m³) |
| o3 | FloatField | O₃ (μg/m³) |

---

## 📄 开源协议

本项目仅供学习参考，数据来源于 [天气后报网](https://www.tianqihoubao.com/)。

---

> **深圳职业技术大学 · 人工智能学院 · 2026 届毕业设计**
