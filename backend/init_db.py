# -*- coding: utf-8 -*-
"""数据库初始化与轻量字段迁移：
- create_all 自动建表
- 对已存在的老表（material / stock_log）补充新列
- 写入 GlobalStage 初始行（id=1, check_code=1）
- 默认管理员 / 分类 / 激活码 / 用户配置
"""
from database import engine, Base, SessionLocal
from core.security import hash_password
from core.version_util import APP_VERSION_MAJOR, APP_VERSION_MINOR, APP_VERSION_PATCH
from models.user import User
from models.category import Category
from models.material import Material
from models.project import Project
from models.project_bom import ProjectBom
from models.stock_log import StockLog
from models.license import License
from models.user_config import UserConfig
from models.conflict import Conflict
from models.backup_snapshot import BackupSnapshot
from models.operation_log import OperationLog
from models.global_stage import GlobalStage
from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from datetime import datetime, timedelta
from sqlalchemy import inspect, text


# 系统默认预设分类（可自定义修改）
DEFAULT_CATEGORIES = [
    ("电子元器件", ["电阻", "电容", "电感/磁珠", "二极管/三极管", "芯片/IC", "晶振", "连接器/端子"]),
    ("五金结构件", ["螺丝/螺母/垫片", "壳体/支架结构件", "防水/密封配件"]),
    ("工具设备", ["手动工具", "电动工具", "测试仪器"]),
    ("耗材辅料", ["焊锡/助焊耗材", "胶带/胶水/固定辅料", "清洁防护耗材"]),
]

# 系统默认用户配置（admin 首次启动写入）
DEFAULT_CONFIGS = {
    # 同步 / 冲突处理
    "sync_freq": "auto",                 # auto / manual / 5min / 15min / 1h
    "conflict_prefer": "latest_side",    # latest_side / prefer_web / prefer_app / manual
    # 备份
    "backup_auto_enable": "1",           # 1/0
    "backup_keep_max_count": "10",
    "backup_keep_max_days": "60",
    # UI
    "theme_key": "tech-dark",
}


def _sqlite_coltype(col_sql: str) -> tuple[str, str, str]:
    """解析 "col_name TYPE ..."，返回 (col_name, col_type, default_const)。"""
    import re
    s = col_sql.strip()
    parts = s.split(None, 2)  # name / type / rest
    name = parts[0]
    ctype = parts[1]
    rest = parts[2] if len(parts) > 2 else ""
    default = ""
    m = re.search(r"DEFAULT\s+(.+?)(?:\s+NOT\s+NULL|\s*$)", rest, re.IGNORECASE)
    if m:
        default = m.group(1).strip().strip("'\"")
    return name, ctype, default


def _add_col_if_missing(table_name: str, col_sql: str) -> str:
    """SQLite ALTER TABLE ADD COLUMN 轻量迁移。

    SQLite 不允许新增列使用非常量 DEFAULT（如 CURRENT_TIMESTAMP）或组合 NOT NULL+动态默认，
    因此统一只加 "name type"（可空），后续通过 UPDATE + 业务写入补值。
    返回实际添加的列名（已存在或表不存在返回 ""）。
    """
    insp = inspect(engine)
    if table_name not in insp.get_table_names():
        return ""
    cols = {c["name"] for c in insp.get_columns(table_name)}
    name, ctype, _default = _sqlite_coltype(col_sql)
    if name in cols:
        return ""
    with engine.connect() as conn:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN "{name}" {ctype}'))
        conn.commit()
        print(f"[迁移] {table_name} 表已添加列: {name} {ctype}")
    return name


def _migrate_columns():
    # V1.2 新增列（SQLite：只加 name+type，默认值和 NOT NULL 通过 UPDATE + 业务写入保证）
    material_cols = [
        "server_commit_ts DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL",
    ]
    stock_log_cols = [
        "server_commit_ts DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL",
        "local_device_ts DATETIME",
        "time_correction_flag VARCHAR(20) DEFAULT '' NOT NULL",
        "source VARCHAR(16) DEFAULT 'web' NOT NULL",
        "device_id VARCHAR(128) DEFAULT '' NOT NULL",
        "client_op_idempotency_key VARCHAR(64) DEFAULT '' NOT NULL",
        "invalid INTEGER DEFAULT 0 NOT NULL",
        "revoke_status VARCHAR(16) DEFAULT 'ok' NOT NULL",
    ]
    for c in material_cols:
        _add_col_if_missing("material", c)
    for c in stock_log_cols:
        _add_col_if_missing("stock_log", c)

    # 回填默认值（兼容 SQLite 只能用字符串常量或 CURRENT_TIMESTAMP 的字面等价）
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.connect() as conn:
        def _fill_null(table: str, col: str, value_expr: str, use_str_now: bool = False):
            rows = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")).scalar() or 0
            if rows > 0:
                val = now_str if use_str_now else value_expr
                conn.execute(text(f"UPDATE {table} SET {col} = {val} WHERE {col} IS NULL"))
                conn.commit()
                print(f"[迁移] {table}.{col} 已回填 {rows} 行")

        # material.server_commit_ts：老数据用 create_time，没有就用 now
        rc = conn.execute(text("SELECT COUNT(*) FROM material WHERE server_commit_ts IS NULL")).scalar() or 0
        if rc > 0:
            conn.execute(text(
                "UPDATE material SET server_commit_ts = COALESCE(create_time, :t) WHERE server_commit_ts IS NULL"
            ), {"t": now_str})
            conn.commit()
            print(f"[迁移] material.server_commit_ts 已回填 {rc} 行")

        # stock_log.server_commit_ts
        rc = conn.execute(text("SELECT COUNT(*) FROM stock_log WHERE server_commit_ts IS NULL")).scalar() or 0
        if rc > 0:
            conn.execute(text(
                "UPDATE stock_log SET server_commit_ts = COALESCE(create_time, :t) WHERE server_commit_ts IS NULL"
            ), {"t": now_str})
            conn.commit()
            print(f"[迁移] stock_log.server_commit_ts 已回填 {rc} 行")

        # stock_log 其余有字面默认的列
        _fill_null("stock_log", "time_correction_flag", "''")
        _fill_null("stock_log", "source", "'web'")
        _fill_null("stock_log", "device_id", "''")
        _fill_null("stock_log", "client_op_idempotency_key", "''")
        _fill_null("stock_log", "invalid", "0")
        _fill_null("stock_log", "revoke_status", "'ok'")


def _ensure_global_stage(db) -> None:
    row = db.query(GlobalStage).filter(GlobalStage.id == 1).first()
    if not row:
        db.add(GlobalStage(id=1, global_check_code=1))
        db.commit()
        print("[初始化] global_stage 初始行已写入 (global_check_code=1)")


def _ensure_default_configs(db, username: str) -> None:
    for key, val in DEFAULT_CONFIGS.items():
        exists = db.query(UserConfig).filter(UserConfig.username == username, UserConfig.key == key).first()
        if not exists:
            db.add(UserConfig(username=username, key=key, value=val))
    db.commit()


def init_db():
    # 让 ORM 识别全部模型，create_all 一次建完
    from models import __all__ as _models_all  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 列迁移（针对旧版本升级）
    _migrate_columns()

    db = SessionLocal()
    try:
        # 0. GlobalStage
        _ensure_global_stage(db)

        # 1. 默认管理员
        admin = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            )
            db.add(admin)
            db.commit()
            print(f"[初始化] 默认管理员已创建：{DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
        else:
            print("[初始化] 管理员账号已存在，跳过创建")

        # 2. 默认分类
        if db.query(Category).count() == 0:
            for idx, (l1_name, l2_list) in enumerate(DEFAULT_CATEGORIES):
                l1 = Category(name=l1_name, parent_id=0, level=1, sort=idx)
                db.add(l1)
                db.commit()
                db.refresh(l1)
                for j, l2_name in enumerate(l2_list):
                    l2 = Category(name=l2_name, parent_id=l1.id, level=2, sort=j)
                    db.add(l2)
                db.commit()
            print(f"[初始化] 默认二级分类已写入 {len(DEFAULT_CATEGORIES)} 个一级分类")
        else:
            print("[初始化] 分类数据已存在，跳过默认分类写入")

        # 3. 默认测试激活码
        if db.query(License).count() == 0:
            far_future = datetime.now() + timedelta(days=365 * 99)
            one_year = datetime.now() + timedelta(days=365)
            db.add_all([
                License(license_code="DEV-FOREVER", device_id="", max_bindings=9999,
                        expire_at=far_future, remark="开发专用 —— 永久 + 不限制设备数"),
                License(license_code="DEV-1YEAR-1DEV", device_id="", max_bindings=1,
                        expire_at=one_year, remark="开发专用 —— 1年 / 1台设备"),
            ])
            db.commit()
            print("[初始化] 默认测试激活码已写入：DEV-FOREVER / DEV-1YEAR-1DEV")
        else:
            print("[初始化] 激活码表已有数据，跳过默认写入")

        # 4. 默认配置
        _ensure_default_configs(db, DEFAULT_ADMIN_USERNAME)
    finally:
        db.close()
