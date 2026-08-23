# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success, fail
from models.stock_log import StockLog
from models.material import Material
from models.project import Project

router = APIRouter()


class _BatchDeleteIn(BaseModel):
    ids: list[int]


def _rollback_log(log: StockLog, db: Session) -> tuple[bool, str]:
    """回退单条流水对库存的影响。返回 (是否允许删除, 失败原因)。
    物料已删除 → 跳过回退，允许删除。
    out_project → 拒绝（涉及BOM状态，无法简单回退）。
    回退后库存为负 → 拒绝。
    """
    m = db.query(Material).filter(Material.id == log.material_id).first()
    if not m:
        # 物料已删除，库存已不存在，无需回退
        return True, ""

    if log.log_type == "in":
        new_num = m.stock_total_num - log.num
        new_cost = m.stock_total_cost - log.cost
        if new_num < 0:
            return False, f"物料「{m.name}」回退后库存为 {round(new_num, 2)}，不允许删除（可能后续已有出库依赖）"
        m.stock_total_num = round(new_num, 6)
        m.stock_total_cost = round(new_cost, 6)
        m.stock_avg_price = round(new_cost / new_num, 6) if new_num > 0 else 0.0

    elif log.log_type == "out_temp":
        # num 为负，减负数 = 加回
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
        # num 为负，减负数 = 加回
        new_lock = m.lock_num - log.num
        if new_lock > m.stock_total_num:
            return False, f"物料「{m.name}」回退后锁定量超过库存，不允许删除"
        m.lock_num = round(new_lock, 6)

    elif log.log_type == "out_project":
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
        q = q.filter(StockLog.create_time >= start_time)
    if end_time:
        q = q.filter(StockLog.create_time <= end_time + " 23:59:59")
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
    items = db.query(StockLog).order_by(StockLog.id.desc()).limit(limit).all()
    return success([_log_to_dict(l, db) for l in items])


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
    # 预检：全部通过后才执行，保证原子性
    for l in items:
        ok, msg = _rollback_log(l, db)
        if not ok:
            db.rollback()
            return fail(msg)
    for l in items:
        db.delete(l)
    db.commit()
    return success({"deleted": len(items)}, f"批量删除成功，共 {len(items)} 条，库存已同步回退")
