# -*- coding: utf-8 -*-
"""
数据库初始化：
  首次启动自动建表、创建默认管理员账号、写入系统默认二级分类、写入默认测试激活码
"""
from database import engine, Base, SessionLocal
from core.security import hash_password
from models.user import User
from models.category import Category
from models.material import Material
from models.project import Project
from models.project_bom import ProjectBom
from models.stock_log import StockLog
from models.license import License
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


def _migrate_material_columns():
    """为已存在的 material 表补充 code / unit / price_unit 列（SQLite ALTER TABLE ADD COLUMN）"""
    insp = inspect(engine)
    if "material" not in insp.get_table_names():
        return  # 表还没建，create_all 会处理
    existing = {c["name"] for c in insp.get_columns("material")}
    with engine.connect() as conn:
        if "code" not in existing:
            conn.execute(text("ALTER TABLE material ADD COLUMN code VARCHAR(64) DEFAULT '' NOT NULL"))
            print("[迁移] material 表已添加 code 列")
        if "unit" not in existing:
            conn.execute(text("ALTER TABLE material ADD COLUMN unit VARCHAR(20) DEFAULT '个' NOT NULL"))
            print("[迁移] material 表已添加 unit 列")
        if "price_unit" not in existing:
            conn.execute(text("ALTER TABLE material ADD COLUMN price_unit VARCHAR(10) DEFAULT '¥' NOT NULL"))
            print("[迁移] material 表已添加 price_unit 列")
        conn.commit()


def init_db():
    """建表 + 初始化数据"""
    # 导入所有模型以确保建表
    Base.metadata.create_all(bind=engine)

    # 轻量迁移：为已存在的 material 表补充 code / unit 列（首次升级到含编码/单位版本时执行）
    _migrate_material_columns()

    db = SessionLocal()
    try:
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

        # 3. 默认测试激活码 —— 首次启动自动写入，方便 App 调试
        #   DEV-FOREVER    —— 永久不绑定设备（不限台数，开发专用）
        #   DEV-1YEAR-1DEV —— 1年/1台设备
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
    finally:
        db.close()
