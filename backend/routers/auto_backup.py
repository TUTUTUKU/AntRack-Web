# -*- coding: utf-8 -*-
"""自动备份配置管理：获取/更新配置、手动触发自动备份策略检查、立即执行一次备份。"""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.response import success, fail
from core.version_util import get_app_version, parse_version
from database import get_db
from dependencies import get_current_user, is_admin_user, principal_username
from models.auto_backup_config import AutoBackupConfig
from models.backup_snapshot import BackupSnapshot
from routers.backup import _gen_full_backup_zip
from datetime import timedelta

router = APIRouter()


# ---- Pydantic 请求体 ----

class AutoBackupConfigIn(BaseModel):
    enabled: bool = True
    strategy: str = Field("weekly", description="interval / daily / weekly / monthly / cron")
    # interval
    interval_value: int = 60
    interval_unit: str = "minutes"  # minutes / hours
    # daily
    daily_hour: int = 2
    daily_minute: int = 0
    # weekly
    weekly_days: str = "0"  # 逗号分隔 0-6
    weekly_hour: int = 2
    weekly_minute: int = 0
    # monthly
    monthly_day: int = 1  # 1-28
    monthly_hour: int = 2
    monthly_minute: int = 0
    # cron
    cron_expr: str = ""
    # 保留策略
    retention_mode: str = "count"  # count / days
    retention_count: int = 10
    retention_days: int = 60
    # 存储路径
    storage_path: str = "data/backups"
    # 并发控制
    forbid_concurrent: bool = True


# ---- 工具函数 ----

def _cfg_out(c: AutoBackupConfig) -> dict:
    return {
        "id": c.id,
        "enabled": c.enabled,
        "strategy": c.strategy,
        "interval_value": c.interval_value,
        "interval_unit": c.interval_unit,
        "daily_hour": c.daily_hour,
        "daily_minute": c.daily_minute,
        "weekly_days": c.weekly_days,
        "weekly_hour": c.weekly_hour,
        "weekly_minute": c.weekly_minute,
        "monthly_day": c.monthly_day,
        "monthly_hour": c.monthly_hour,
        "monthly_minute": c.monthly_minute,
        "cron_expr": c.cron_expr,
        "retention_mode": c.retention_mode,
        "retention_count": c.retention_count,
        "retention_days": c.retention_days,
        "storage_path": c.storage_path,
        "forbid_concurrent": c.forbid_concurrent,
        "last_run_at": c.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if c.last_run_at else "",
        "last_run_status": c.last_run_status or "",
        "last_run_msg": c.last_run_msg or "",
        "update_time": c.update_time.strftime("%Y-%m-%d %H:%M:%S") if c.update_time else "",
        "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S") if c.create_time else "",
    }


def _ensure_default_config(db: Session) -> AutoBackupConfig:
    """确保配置行存在（id=1）。"""
    cfg = db.query(AutoBackupConfig).filter(AutoBackupConfig.id == 1).first()
    if not cfg:
        cfg = AutoBackupConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


# ---- 路由 ----

@router.get("/config")
def get_config(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    cfg = _ensure_default_config(db)
    return success(_cfg_out(cfg))


@router.put("/config")
def update_config(
    body: AutoBackupConfigIn,
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """更新自动备份配置（仅管理员）。修改后即时生效，无需重启。"""
    if not is_admin_user(user):
        return fail("仅管理员可修改自动备份配置", code=403)

    # 参数校验
    if body.strategy not in ("interval", "daily", "weekly", "monthly"):
        return fail("策略类型不正确")
    if body.strategy == "interval":
        if body.interval_unit == "minutes" and body.interval_value < 10:
            return fail("间隔策略最小间隔为 10 分钟")
        if body.interval_value < 1:
            return fail("间隔数值必须大于 0")
    if body.strategy == "monthly":
        if not (1 <= body.monthly_day <= 28):
            return fail("每月日期限 1-28 日")
    if body.retention_mode not in ("count", "days"):
        return fail("保留策略模式不正确")
    if body.retention_mode == "count" and body.retention_count < 1:
        return fail("保留份数必须大于 0")
    if body.retention_mode == "days" and body.retention_days < 1:
        return fail("保留天数必须大于 0")

    cfg = _ensure_default_config(db)
    cfg.enabled = body.enabled
    cfg.strategy = body.strategy
    cfg.interval_value = body.interval_value
    cfg.interval_unit = body.interval_unit
    cfg.daily_hour = body.daily_hour
    cfg.daily_minute = body.daily_minute
    cfg.weekly_days = body.weekly_days
    cfg.weekly_hour = body.weekly_hour
    cfg.weekly_minute = body.weekly_minute
    cfg.monthly_day = body.monthly_day
    cfg.monthly_hour = body.monthly_hour
    cfg.monthly_minute = body.monthly_minute
    cfg.cron_expr = body.cron_expr.strip()
    cfg.retention_mode = body.retention_mode
    cfg.retention_count = body.retention_count
    cfg.retention_days = body.retention_days
    cfg.storage_path = body.storage_path.strip() or "data/backups"
    cfg.forbid_concurrent = body.forbid_concurrent
    cfg.update_time = datetime.now()
    db.commit()
    db.refresh(cfg)

    # 即时生效：调度器每次 tick 都重新读取配置，无需重启
    return success(_cfg_out(cfg), "配置已更新，即时生效")


@router.post("/run-now")
def run_now(
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """手动触发一次自动备份（不受定时策略影响，仅管理员）。"""
    if not is_admin_user(user):
        return fail("仅管理员可执行备份操作", code=403)
    try:
        ver = parse_version(get_app_version())
        info = _gen_full_backup_zip(db, trigger="auto", note=f"手动触发自动备份 by {principal_username(user)}")
        cfg = _ensure_default_config(db)
        _expiry = datetime.now() + timedelta(days=cfg.retention_days if cfg.retention_mode == "days" else 60)
        snap = BackupSnapshot(
            trigger="auto",
            version_x=ver[0], version_y=ver[1], version_z=ver[2],
            file_path=info["relative_path"],
            file_size=int(info.get("file_size") or 0),
            note=f"手动触发自动备份 by {principal_username(user)}",
            expiry_time=_expiry,
        )
        db.add(snap)

        # 更新配置状态
        cfg.last_run_at = datetime.now()
        cfg.last_run_status = "success"
        cfg.last_run_msg = f"手动触发成功: snapshot_id={snap.id}"
        db.commit()

        # 执行保留策略清理
        _apply_retention_static(db, cfg)

        return success({"snapshot_id": snap.id, "name": f"WEB#{snap.id}"}, "备份执行成功")
    except Exception as e:
        db.rollback()
        # 写入失败日志
        from core.op_log_service import write_op_log
        try:
            write_op_log(db, username=principal_username(user), source="web",
                         action="auto_backup_failed", detail={"error": str(e)})
            cfg = _ensure_default_config(db)
            cfg.last_run_at = datetime.now()
            cfg.last_run_status = "failed"
            cfg.last_run_msg = str(e)[:500]
            db.commit()
        except Exception:
            pass
        return fail(f"备份执行失败: {e}")


def _apply_retention_static(db: Session, cfg: AutoBackupConfig):
    """保留策略清理（静态函数，路由中直接调用）。"""
    from pathlib import Path
    from config import BASE_DIR
    import os
    now = datetime.now()
    rows = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).all()
    removed_paths = []
    if cfg.retention_mode == "count":
        for idx, r in enumerate(rows):
            if idx >= cfg.retention_count:
                removed_paths.append(r.file_path)
                db.delete(r)
    elif cfg.retention_mode == "days":
        for r in rows:
            if r.create_time and (now - r.create_time).days > cfg.retention_days:
                removed_paths.append(r.file_path)
                db.delete(r)
    for p in removed_paths:
        if not p:
            continue
        full = Path(p) if os.path.isabs(p) else (BASE_DIR / p)
        try:
            if full.exists():
                full.unlink()
        except Exception:
            pass
    db.commit()
