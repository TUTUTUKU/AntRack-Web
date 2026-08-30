# -*- coding: utf-8 -*-
"""业务核心公共函数：时间解析 / 阶段校验码 / 幂等检查"""
from __future__ import annotations
import re
from datetime import datetime
from sqlalchemy.orm import Session
from models.global_stage import GlobalStage
from models.stock_log import StockLog


_DT_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?"
)


def parse_iso_dt(s: str | None) -> datetime | None:
    """宽松解析 YYYY-MM-DD HH:MM:SS / ISO 格式；解析失败返回 None"""
    if not s:
        return None
    s = str(s).strip()
    m = _DT_RE.search(s)
    if not m:
        return None
    y, mo, d, h, mi = (int(x) for x in m.groups()[:5])
    se = int(m.group(6) or 0)
    try:
        return datetime(y, mo, d, h, mi, se)
    except ValueError:
        return None


def fmt_dt(d: datetime | None) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else ""


def get_global_check_code(db: Session) -> int:
    row = db.query(GlobalStage).filter(GlobalStage.id == 1).first()
    if not row:
        row = GlobalStage(id=1, global_check_code=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row.global_check_code


def bump_global_check_code(db: Session) -> int:
    """批量物料/配置变更时 +1（单条普通修改不要调用）"""
    row = db.query(GlobalStage).filter(GlobalStage.id == 1).with_for_update().first()
    if not row:
        row = GlobalStage(id=1, global_check_code=1)
        db.add(row)
        db.flush()
    row.global_check_code = (row.global_check_code or 0) + 1
    db.flush()
    return row.global_check_code


def check_idempotency(db: Session, key: str) -> StockLog | None:
    """幂等检查：若同一 key 已处理过，返回已有的流水；否则返回 None"""
    if not key:
        return None
    return db.query(StockLog).filter(StockLog.client_op_idempotency_key == key).first()
