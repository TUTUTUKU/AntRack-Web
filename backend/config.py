# -*- coding: utf-8 -*-
"""
全局配置文件
V1.0 固定配置，单管理员模式，SQLite 单文件数据库
"""
import os
from pathlib import Path

# ============ 路径配置 ============
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "data" / "stock.db"

# 确保目录存在
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ============ 数据库配置 ============
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# ============ 鉴权配置 ============
# 生产环境通过环境变量注入，避免密钥被提交到 Git 仓库
#   Docker:  在 docker-compose.yml 里配 environment: ANTRACK_SECRET_KEY=你的随机长字符串
#   本地:    直接用下方默认值即可，无需额外配置
SECRET_KEY = os.getenv(
    "ANTRACK_SECRET_KEY",
    "antrack-ant-rack-system-secret-key-2024-local-dev-only"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天有效

# ============ 默认管理员（首次启动自动创建）============
# 生产环境强烈建议在启动后立刻通过"系统设置 → 修改密码"改掉默认值，
# 或通过环境变量覆盖（首次初始化时才会用这两个值创建账号）
DEFAULT_ADMIN_USERNAME = os.getenv("ANTRACK_DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ANTRACK_DEFAULT_ADMIN_PASSWORD", "admin123")

# ============ 静态资源 ============
STATIC_URL_PREFIX = "/static"
