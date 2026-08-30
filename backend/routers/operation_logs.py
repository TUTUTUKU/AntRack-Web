# -*- coding: utf-8 -*-
"""操作日志接口"""
from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success, fail
from core.biz_common import parse_iso_dt
from core.undo_service import can_undo
from models.operation_log import OperationLog
from models.stock_log import StockLog

router = APIRouter()


def _out(o: OperationLog) -> dict:
    undo_flag = False
    # 关联库存流水的日志用流水判断撤销窗口
    if o.related_log_id and o.action in ("stock_in", "stock_out_temp", "stock_out_project", "bom_lock", "bom_unlock"):
        from database import SessionLocal
        db2 = SessionLocal()
        try:
            log = db2.query(StockLog).filter(StockLog.id == int(o.related_log_id)).first()
            ok, _ = can_undo(log)
            undo_flag = ok and (o.revoke_status == "ok")
        finally:
            db2.close()
    try:
        det = json.loads(o.detail_json or "{}")
    except Exception:
        det = {}
    return {
        "id": o.id,
        "username": o.username,
        "source": o.source,
        "device_id": o.device_id or "",
        "action": o.action,
        "material_id": o.material_id,
        "project_id": o.project_id,
        "related_log_id": o.related_log_id,
        "detail": det,
        "ip": o.ip or "",
        "effective_time": o.effective_time.strftime("%Y-%m-%d %H:%M:%S") if o.effective_time else "",
        "revoke_status": o.revoke_status or "ok",
        "can_undo": undo_flag,
    }


@router.get("/list")
def list_logs(
    page: int = 1,
    page_size: int = 20,
    material_id: int | None = None,
    project_id: int | None = None,
    start_time: str = "",
    end_time: str = "",
    action: str = "",
    source: str = "",
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(OperationLog)
    if material_id:
        q = q.filter(OperationLog.material_id == material_id)
    if project_id:
        q = q.filter(OperationLog.project_id == project_id)
    if action:
        q = q.filter(OperationLog.action == action)
    if source:
        q = q.filter(OperationLog.source == source)
    if start_time:
        st = parse_iso_dt(start_time)
        if st:
            q = q.filter(OperationLog.effective_time >= st)
    if end_time:
        et = parse_iso_dt(end_time)
        if et:
            q = q.filter(OperationLog.effective_time <= et)
    total = q.count()
    items = q.order_by(OperationLog.effective_time.desc(), OperationLog.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return success({
        "total": total, "page": page, "page_size": page_size,
        "list": [_out(o) for o in items],
    })
