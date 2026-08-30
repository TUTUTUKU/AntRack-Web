# -*- coding: utf-8 -*-
"""
调度器：自动备份（5种时间策略）+ 过期清理。

时间策略：
1. interval  — 按 N 分钟/N小时间隔执行（最小 10 分钟）
2. daily     — 每天固定时:分执行
3. weekly    — 多选周一到周日 + 时:分执行
4. monthly    — 每月指定日期(1-28) + 时:分执行
5. cron       — Cron 表达式（高级模式）

配套：
- 保留策略：保留 N 个文件 / 保留 N 天
- 禁止并发：上次未完成不触发下次
- 备份失败写入操作日志
- 修改配置即时生效（每次 tick 重新读取配置）
"""
from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from database import SessionLocal
from models.auto_backup_config import AutoBackupConfig
from models.backup_snapshot import BackupSnapshot
from models.conflict import Conflict
from models.operation_log import OperationLog
from config import BASE_DIR
from core.version_util import get_app_version, parse_version
from core.op_log_service import write_op_log
from routers.backup import _gen_full_backup_zip


# ========= Cron 表达式解析（5字段：分 时 日 月 周）=========

def _cron_match(expr: str, dt: datetime) -> bool:
    """简易 cron 匹配：判断 dt 是否匹配 5 字段 cron 表达式。"""
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    minute_p, hour_p, day_p, month_p, dow_p = parts
    return (
        _cron_field_match(minute_p, dt.minute, 0, 59) and
        _cron_field_match(hour_p, dt.hour, 0, 23) and
        _cron_field_match(day_p, dt.day, 1, 31) and
        _cron_field_match(month_p, dt.month, 1, 12) and
        _cron_field_match(dow_p, dt.weekday(), 0, 6)
    )


def _cron_field_match(field: str, value: int, lo: int, hi: int) -> bool:
    """匹配单个 cron 字段。"""
    for part in field.split(","):
        if part == "*":
            continue
        step = 1
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
            part = base
        if part == "*":
            for v in range(lo, hi + 1, step):
                if v == value:
                    return True
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            for v in range(a, b + 1, step):
                if v == value:
                    return True
            continue
        if int(part) == value:
            return True
    return True  # 没有匹配项说明该字段不限制（空逗号段不常见）


class AntrackScheduler:
    _instance = None
    _thread: threading.Thread | None = None
    _stop = threading.Event()
    _backup_running = False  # 并发控制标志
    _lock = threading.Lock()

    def __init__(self):
        self._last_tick_at: datetime | None = None
        self._last_cleanup_at: datetime | None = None
        self._last_backup_at: datetime | None = None  # 上次成功执行自动备份的时间

    @classmethod
    def start(cls) -> "AntrackScheduler":
        if cls._instance is None:
            cls._instance = AntrackScheduler()
            cls._instance._run()
            print("[scheduler] 后台调度线程已启动（自动备份 / 过期清理）")
        return cls._instance

    @classmethod
    def stop(cls) -> None:
        if cls._instance:
            cls._instance._stop.set()

    # ----- 调度循环 -----
    def _run(self):
        def loop():
            while not self._stop.is_set():
                try:
                    self._tick()
                except Exception as e:
                    print(f"[scheduler] tick error: {e}")
                for _ in range(30):  # 30秒 tick
                    if self._stop.is_set():
                        return
                    time.sleep(1)
        self._thread = threading.Thread(target=loop, name="antrack-scheduler", daemon=True)
        self._thread.start()

    def _tick(self):
        now = datetime.now()
        self._last_tick_at = now

        # 1. 自动备份
        self._check_auto_backup(now)

        # 2. 清理：每 6 小时
        if self._last_cleanup_at is None or (now - self._last_cleanup_at) >= timedelta(hours=6):
            try:
                self._do_cleanups()
            except Exception as e:
                print(f"[scheduler] cleanup error: {e}")
            self._last_cleanup_at = now

    # ----- 自动备份检查 -----
    def _check_auto_backup(self, now: datetime):
        db = SessionLocal()
        try:
            cfg = db.query(AutoBackupConfig).filter(AutoBackupConfig.id == 1).first()
            if not cfg or not cfg.enabled:
                return

            should_run = self._should_run(cfg, now)
            if not should_run:
                return

            # 禁止并发
            if cfg.forbid_concurrent and self._backup_running:
                print("[scheduler] 上次自动备份仍在执行，跳过本次触发")
                return

            # 执行备份
            self._do_auto_backup(db, cfg)
        finally:
            db.close()

    def _should_run(self, cfg: AutoBackupConfig, now: datetime) -> bool:
        """判断当前时刻是否应该触发自动备份。"""
        strategy = cfg.strategy

        if strategy == "interval":
            if not self._last_backup_at:
                return True  # 首次启动时执行一次
            unit = cfg.interval_unit
            val = max(cfg.interval_value, 10) if unit == "minutes" else cfg.interval_value
            delta = timedelta(minutes=val) if unit == "minutes" else timedelta(hours=val)
            return (now - self._last_backup_at) >= delta

        if strategy == "daily":
            if self._last_backup_at and self._last_backup_at.date() == now.date():
                return False
            return now.hour == cfg.daily_hour and now.minute == cfg.daily_minute

        if strategy == "weekly":
            days = [int(d) for d in (cfg.weekly_days or "").split(",") if d.strip()]
            if now.weekday() not in days:
                return False
            if self._last_backup_at and self._last_backup_at.date() == now.date():
                return False
            return now.hour == cfg.weekly_hour and now.minute == cfg.weekly_minute

        if strategy == "monthly":
            if self._last_backup_at and self._last_backup_at.month == now.month and self._last_backup_at.year == now.year:
                return False
            return now.day == cfg.monthly_day and now.hour == cfg.monthly_hour and now.minute == cfg.monthly_minute

        return False

    # ----- 实际备份执行 -----
    def _do_auto_backup(self, db, cfg: AutoBackupConfig):
        with self._lock:
            self._backup_running = True

        try:
            ver = parse_version(get_app_version())
            info = _gen_full_backup_zip(db, trigger="auto", note="自动备份")
            _expiry = datetime.now() + timedelta(days=cfg.retention_days if cfg.retention_mode == "days" else 60)
            snap = BackupSnapshot(
                trigger="auto",
                version_x=ver[0], version_y=ver[1], version_z=ver[2],
                file_path=info["relative_path"],
                file_size=int(info.get("file_size") or 0),
                note="自动备份",
                expiry_time=_expiry,
            )
            db.add(snap)
            db.commit()

            cfg.last_run_at = datetime.now()
            cfg.last_run_status = "success"
            cfg.last_run_msg = f"备份成功: snapshot_id={snap.id}"
            db.commit()

            self._last_backup_at = datetime.now()
            print(f"[scheduler] 自动备份已生成: snapshot_id={snap.id}")

            # 执行保留策略清理
            self._apply_retention(db, cfg)

        except Exception as e:
            db.rollback()
            err_msg = str(e)
            print(f"[scheduler] 自动备份失败: {err_msg}")
            # 备份失败写入操作日志
            try:
                write_op_log(db, username="system", source="web", action="auto_backup_failed",
                             detail={"error": err_msg})
                db.commit()
            except Exception:
                pass
            # 更新配置状态
            try:
                cfg2 = db.query(AutoBackupConfig).filter(AutoBackupConfig.id == 1).first()
                if cfg2:
                    cfg2.last_run_at = datetime.now()
                    cfg2.last_run_status = "failed"
                    cfg2.last_run_msg = err_msg[:500]
                    db.commit()
            except Exception:
                pass
        finally:
            with self._lock:
                self._backup_running = False

    # ----- 保留策略清理 -----
    def _apply_retention(self, db, cfg: AutoBackupConfig):
        """根据保留策略清理旧备份。"""
        now = datetime.now()
        rows = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).all()

        removed_paths = []
        if cfg.retention_mode == "count":
            max_count = cfg.retention_count
            for idx, r in enumerate(rows):
                if idx >= max_count:
                    removed_paths.append(r.file_path)
                    db.delete(r)
        elif cfg.retention_mode == "days":
            max_days = cfg.retention_days
            for r in rows:
                if r.create_time and (now - r.create_time).days > max_days:
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
        if removed_paths:
            print(f"[scheduler] 保留策略已清理 {len(removed_paths)} 份旧备份")

    # ----- 过期清理（保留原有逻辑）-----
    def _do_cleanups(self):
        db = SessionLocal()
        try:
            from models.user_config import UserConfig
            from init_db import DEFAULT_CONFIGS
            def cfg(k: str) -> str:
                row = db.query(UserConfig).filter(UserConfig.username == "admin", UserConfig.key == k).first()
                return row.value if row else DEFAULT_CONFIGS.get(k, "")

            max_count = int(cfg("backup_keep_max_count") or "10")
            max_days = int(cfg("backup_keep_max_days") or "60")

            current_ver = parse_version(get_app_version())
            now = datetime.now()
            rows = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).all()

            out_of_major = [r for r in rows if r.version_x != current_ver[0]]
            keep = [r for r in rows if r.version_x == current_ver[0]]

            removed_paths = []
            for r in out_of_major:
                removed_paths.append(r.file_path)
                db.delete(r)
            for idx, r in enumerate(keep):
                aged_out = (max_days > 0) and ((now - r.create_time).days > max_days)
                over_count = idx >= max_count
                if aged_out or over_count:
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
            if removed_paths:
                print(f"[scheduler] 已清理过期备份 {len(removed_paths)} 份")

            # 冲突记录保留 1 年
            one_year_ago = now - timedelta(days=365)
            n = db.query(Conflict).filter(Conflict.create_time < one_year_ago).delete()
            if n:
                print(f"[scheduler] 清理过期冲突记录 {n} 条")

            # 操作日志保留 1 年
            n2 = db.query(OperationLog).filter(OperationLog.create_time < one_year_ago).delete()
            if n2:
                print(f"[scheduler] 清理过期操作日志 {n2} 条")
            db.commit()
        finally:
            db.close()
