# -*- coding: utf-8 -*-
"""
调度器：
1. 每周一自动备份一次
2. 每 6 小时清理一次：过期备份、过期冲突记录（保留 1 年）、过期操作日志（保留 1 年）
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
import time

from database import SessionLocal
from models.backup_snapshot import BackupSnapshot
from models.conflict import Conflict
from models.operation_log import OperationLog
from config import BASE_DIR
from core.version_util import get_app_version, parse_version
from routers.backup import _gen_full_backup_zip, _SNAPSHOT_SUBDIR


class AntrackScheduler:
    _instance = None
    _thread: threading.Thread | None = None
    _stop = threading.Event()

    def __init__(self):
        self._last_auto_backup_date: str | None = None
        self._last_cleanup_at: datetime | None = None
        self._last_over_1h_at: datetime | None = None

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
                for _ in range(60):
                    if self._stop.is_set():
                        return
                    time.sleep(1)
        self._thread = threading.Thread(target=loop, name="antrack-scheduler", daemon=True)
        self._thread.start()

    def _tick(self):
        now = datetime.now()
        weekday = now.strftime("%A")
        # 1. 自动备份：每周一 白天（00:00-23:59 任何时间首次 tick 都触发一次，避免时间漂移）
        if weekday == "Monday" and self._last_auto_backup_date != now.strftime("%Y-%m-%d"):
            try:
                self._do_auto_backup()
            except Exception as e:
                print(f"[scheduler] auto backup error: {e}")
            self._last_auto_backup_date = now.strftime("%Y-%m-%d")

        # 2. 清理：每 6 小时
        if self._last_cleanup_at is None or (now - self._last_cleanup_at) >= timedelta(hours=6):
            try:
                self._do_cleanups()
            except Exception as e:
                print(f"[scheduler] cleanup error: {e}")
            self._last_cleanup_at = now

    # ----- 实际任务 -----
    def _do_auto_backup(self):
        db = SessionLocal()
        try:
            from models.user_config import UserConfig
            from init_db import DEFAULT_CONFIGS
            def cfg(k: str) -> str:
                row = db.query(UserConfig).filter(UserConfig.username == "admin", UserConfig.key == k).first()
                return row.value if row else DEFAULT_CONFIGS.get(k, "")
            if cfg("backup_auto_enable") != "1":
                print("[scheduler] 自动备份已在设置中关闭，跳过")
                return
            ver = parse_version(get_app_version())
            info = _gen_full_backup_zip(db, trigger="auto", note="scheduler auto backup")
            _expiry = datetime.now() + timedelta(days=60)
            snap = BackupSnapshot(
                trigger="auto",
                version_x=ver[0], version_y=ver[1], version_z=ver[2],
                file_path=info["relative_path"],
                file_size=int(info.get("file_size") or 0),
                note="scheduler auto backup",
                expiry_time=_expiry,
            )
            db.add(snap)
            db.commit()
            print(f"[scheduler] 自动备份已生成：snapshot_id={snap.id}")
        finally:
            db.close()

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

            # ① 备份清理：双条件（max_count / max_days）+ 大版本升级清旧备份
            current_ver = parse_version(get_app_version())
            now = datetime.now()
            rows = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).all()

            # 大版本不一致全部清除
            out_of_major = [r for r in rows if r.version_x != current_ver[0]]
            keep = [r for r in rows if r.version_x == current_ver[0]]

            removed_ids: list[int] = []
            removed_paths: list[str] = []

            for r in out_of_major:
                removed_ids.append(r.id)
                removed_paths.append(r.file_path)
                db.delete(r)

            # 按 id 逆序保留前 max_count 条；超出、过期清除
            for idx, r in enumerate(keep):
                aged_out = (max_days > 0) and ((now - r.create_time).days > max_days)
                over_count = idx >= max_count
                if aged_out or over_count:
                    removed_ids.append(r.id)
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
            if removed_ids:
                print(f"[scheduler] 已清理过期备份 {len(removed_ids)} 份")

            # ② 冲突记录保留 1 年
            one_year_ago = now - timedelta(days=365)
            n = db.query(Conflict).filter(Conflict.create_time < one_year_ago).delete()
            if n:
                print(f"[scheduler] 清理过期冲突记录 {n} 条")

            # ③ 操作日志保留 1 年
            n2 = db.query(OperationLog).filter(OperationLog.create_time < one_year_ago).delete()
            if n2:
                print(f"[scheduler] 清理过期操作日志 {n2} 条")
            db.commit()
        finally:
            db.close()
