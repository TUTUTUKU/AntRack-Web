# -*- coding: utf-8 -*-
from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, principal_username
from core.response import success, fail
from core.biz_common import parse_iso_dt
from core.undo_service import undo_stock_log, can_undo, UNDO_WINDOW_MINUTES
from core.op_log_service import write_op_log
from models.stock_log import StockLog
from models.material import Material
from models.project import Project

router = APIRouter()


class _BatchDeleteIn(BaseModel):
    ids: list[int]


def _rollback_log(log: StockLog, db: Session) -> tuple[bool, str]:
    m = db.query(Material).filter(Material.id == log.material_id).first()
    if not m:
        return True, ""
    if log.log_type == "in":
        new_num = m.stock_total_num - log.num
        new_cost = m.stock_total_cost - log.cost
        if new_num < 0:
            # 回退后库存为负说明后续已有出库依赖，不允许删除
            return False, f"物料「{m.name}」回退后库存为 {round(new_num, 2)}，不允许删除（可能后续已有出库依赖）"
        m.stock_total_num = round(new_num, 6)
        m.stock_total_cost = round(new_cost, 6)
        m.stock_avg_price = round(new_cost / new_num, 6) if new_num > 0 else 0.0
    elif log.log_type == "out_temp":
        new_num = m.stock_total_num - log.num
        new_cost = m.stock_total_cost + log.cost
        m.stock_total_num = round(new_num, 6)
        m.stock_total_cost = round(new_cost, 6)
        m.stock_avg_price = round(new_cost / new_num, 6) if new_num > 0 else 0.0
    elif log.log_type == "lock":
        new_lock = m.lock_num - log.num
        if new_lock < 0:
            return False, f"物料「{m.name}」回退后锁定量为负，不允许删除"
        m.lock_num = round(new_lock, 6)
    elif log.log_type == "unlock":
        new_lock = m.lock_num - log.num
        if new_lock > m.stock_total_num:
            return False, f"物料「{m.name}」回退后锁定量超过库存，不允许删除"
        m.lock_num = round(new_lock, 6)
    elif log.log_type == "out_project":
        # 项目出库流水涉及 BOM 状态，不能直接删除，必须通过项目管理流程调整
        return False, "项目出库流水涉及BOM状态，不可直接删除，请通过项目管理调整"
    return True, ""


def _log_to_dict(log: StockLog, db: Session) -> dict:
    m = db.query(Material).filter(Material.id == log.material_id).first()
    pname = ""
    if log.project_id:
        p = db.query(Project).filter(Project.id == log.project_id).first()
        pname = p.name if p else ""
    type_map = {
        "in": "入库",
        "out_temp": "临时出库",
        "out_project": "项目出库",
        "lock": "锁定",
        "unlock": "解锁",
    }
    can, _ = can_undo(log)
    server_commit_ts = getattr(log, "server_commit_ts", None) or log.create_time
    local_device_ts = getattr(log, "local_device_ts", None)
    ok_undo = can and (getattr(log, "invalid", 0) == 0) and (getattr(log, "revoke_status", "ok") == "ok")
    return {
        "id": log.id,
        "material_id": log.material_id,
        "project_id": log.project_id,
        "log_type": log.log_type,
        "log_type_name": type_map.get(log.log_type, log.log_type),
        "num": log.num,
        "cost": log.cost,
        "avg_price": log.avg_price,
        "remark": log.remark,
        "material_name": m.name if m else "(已删除)",
        "project_name": pname,
        "create_time": log.create_time.strftime("%Y-%m-%d %H:%M:%S") if log.create_time else "",
        "server_commit_ts": server_commit_ts.strftime("%Y-%m-%d %H:%M:%S") if server_commit_ts else "",
        "local_device_ts": local_device_ts.strftime("%Y-%m-%d %H:%M:%S") if local_device_ts else "",
        "time_correction_flag": getattr(log, "time_correction_flag", "") or "",
        "source": getattr(log, "source", "web") or "web",
        "device_id": getattr(log, "device_id", "") or "",
        "invalid": getattr(log, "invalid", 0) or 0,
        "revoke_status": getattr(log, "revoke_status", "ok") or "ok",
        "can_undo": ok_undo,
        "undo_window_minutes": UNDO_WINDOW_MINUTES,
    }


@router.get("/list")
def list_log(
    page: int = 1,
    page_size: int = 20,
    log_type: str = "",
    material_id: int = 0,
    project_id: int = 0,
    start_time: str = "",
    end_time: str = "",
    show_invalid: bool = False,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(StockLog)
    if log_type:
        q = q.filter(StockLog.log_type == log_type)
    if material_id:
        q = q.filter(StockLog.material_id == material_id)
    if project_id:
        q = q.filter(StockLog.project_id == project_id)
    if start_time:
        st = parse_iso_dt(start_time)
        if st:
            q = q.filter(StockLog.server_commit_ts >= st)
    if end_time:
        et = parse_iso_dt(end_time + " 23:59:59" if len(end_time) == 10 else end_time)
        if et:
            q = q.filter(StockLog.server_commit_ts <= et)
    if not show_invalid:
        q = q.filter((StockLog.invalid == 0) | (StockLog.invalid.is_(None)))
    total = q.count()
    items = q.order_by(StockLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return success({
        "total": total, "page": page, "page_size": page_size,
        "list": [_log_to_dict(l, db) for l in items],
    })


@router.get("/recent")
def recent(limit: int = 10, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    if limit > 100:
        limit = 100
    q = db.query(StockLog).filter((StockLog.invalid == 0) | (StockLog.invalid.is_(None)))
    items = q.order_by(StockLog.id.desc()).limit(limit).all()
    return success([_log_to_dict(l, db) for l in items])


@router.post("/undo/{log_id}")
def undo_log(
    log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """撤销窗口内不删除原流水，写入反向补偿流水并把原流水标记 invalid=1 revoke_status=revoked。"""
    client_ip = request.client.host if request.client else ""
    r = undo_stock_log(db, log_id, operator=principal_username(user), ip=client_ip)
    if not r.get("ok"):
        return fail(r.get("msg") or "撤销失败")
    write_op_log(db, username=principal_username(user), source="web", action="undo",
                 related_log_id=log_id, ip=client_ip,
                 detail={"revoked_log_id": log_id, "new_log_id": r.get("log_id")})
    db.commit()
    return success(r, "撤销成功（已生成反向补偿流水）")


@router.delete("/delete/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    log = db.query(StockLog).filter(StockLog.id == log_id).first()
    if not log:
        return fail("流水记录不存在")
    ok, msg = _rollback_log(log, db)
    if not ok:
        return fail(msg)
    db.delete(log)
    db.commit()
    return success({"id": log_id}, "删除成功，库存已同步回退")


@router.post("/delete-batch")
def delete_batch(data: _BatchDeleteIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    ids = list({int(x) for x in data.ids})
    if not ids:
        return fail("未选择任何流水记录")
    items = db.query(StockLog).filter(StockLog.id.in_(ids)).all()
    if not items:
        return fail("所选流水记录不存在，请刷新后重试")
    for l in items:
        ok, msg = _rollback_log(l, db)
        if not ok:
            db.rollback()
            return fail(msg)
    for l in items:
        db.delete(l)
    db.commit()
    return success({"deleted": len(items)}, f"批量删除成功，共 {len(items)} 条，库存已同步回退")
