# -*- coding: utf-8 -*-
"""自动备份配置表：单行配置（id=1），支持5种时间策略 + 保留策略 + 存储路径 + 并发控制。"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from database import Base


class AutoBackupConfig(Base):
    """自动备份配置（全局单行，id 固定为 1）。"""
    __tablename__ = "auto_backup_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ---- 总开关 ----
    enabled = Column(Boolean, default=True, nullable=False)

    # ---- 时间策略：interval / daily / weekly / monthly / cron ----
    strategy = Column(String(16), default="weekly", nullable=False)

    # interval 策略参数
    interval_value = Column(Integer, default=60, nullable=False)       # 数值
    interval_unit = Column(String(8), default="minutes", nullable=False)  # minutes / hours

    # daily 策略参数
    daily_hour = Column(Integer, default=2, nullable=False)
    daily_minute = Column(Integer, default=0, nullable=False)

    # weekly 策略参数
    weekly_days = Column(String(32), default="0", nullable=False)  # 逗号分隔的星期 0-6 (0=周一)
    weekly_hour = Column(Integer, default=2, nullable=False)
    weekly_minute = Column(Integer, default=0, nullable=False)

    # monthly 策略参数
    monthly_day = Column(Integer, default=1, nullable=False)   # 1-28
    monthly_hour = Column(Integer, default=2, nullable=False)
    monthly_minute = Column(Integer, default=0, nullable=False)

    # cron 策略参数
    cron_expr = Column(String(128), default="", nullable=False)

    # ---- 保留策略 ----
    retention_mode = Column(String(8), default="count", nullable=False)  # count / days
    retention_count = Column(Integer, default=10, nullable=False)          # 保留 N 个
    retention_days = Column(Integer, default=60, nullable=False)          # 保留 N 天

    # ---- 存储路径（服务器本地目录，相对 BASE_DIR） ----
    storage_path = Column(String(256), default="data/backups", nullable=False)

    # ---- 并发控制 ----
    forbid_concurrent = Column(Boolean, default=True, nullable=False)

    # ---- 元信息 ----
    last_run_at = Column(DateTime, nullable=True)        # 上次执行时间
    last_run_status = Column(String(16), default="", nullable=False)  # success / failed / ""
    last_run_msg = Column(Text, default="", nullable=False)
    last_next_run_at = Column(DateTime, nullable=True)   # 下次预计执行时间
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    create_time = Column(DateTime, default=datetime.now, nullable=False)
