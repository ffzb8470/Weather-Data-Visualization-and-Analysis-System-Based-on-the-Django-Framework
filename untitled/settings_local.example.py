"""
settings_local.example.py  —— MySQL 配置示例

使用方式：
  1. 将此文件复制为 settings_local.py（与 settings.py 同目录）
  2. 修改数据库连接信息为实际值
  3. 确保 MySQL 中已创建对应数据库并设置字符集：
     CREATE DATABASE IF NOT EXISTS db129
         CHARACTER SET utf8mb4
         COLLATE utf8mb4_unicode_ci;
  4. 运行迁移：
     python manage.py migrate

注意事项：
  - settings_local.py 已在 .gitignore 中（忽略），避免密钥泄露
  - 本文件（.example.py）上传仓库作为参考模板
  - 若 settings_local.py 不存在，系统自动回退到 SQLite
"""

from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db129',               # 数据库名称（需提前创建）
        'USER': 'root',                # MySQL 用户名
        'PASSWORD': '123456',          # MySQL 密码
        'HOST': '127.0.0.1',           # 数据库主机地址
        'PORT': 3306,                  # 数据库端口
        'OPTIONS': {
            'charset': 'utf8mb4',
            # 连接池配置（可选，需安装 django-db-connection-pool）
            # 'pool_size': 10,
            # 'max_overflow': 5,
        },
    }
}
