# -*- coding: utf-8 -*-
"""
库存撤销：5 分钟内的流水可撤销。
按 log_type 做反向库存计算，原流水置为 revoked，并写一条反向补偿流水。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from core.stock_calc import calc_new_avg_price, calc_out_stock
from models.stock_log import StockLog
from models.material import Material
from models.project_bom import ProjectBom


UNDO_WINDOW_MINUTES = 5
CANNOT_UNDO_REASONS = {
    "expired": f"超过 {UNDO_WINDOW_MINUTES} 分钟撤销窗口",
    "already": "这条流水已被撤销 / 失效",
    "nomaterial": "物料不存在",
    "locked": "撤销后物料锁定量或可用库存会为负",
}


def _fmt_dt(d) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else ""


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def can_undo(log: StockLog) -> tuple[bool, str]:
    """判断是否可撤销 + 原因"""
    if not log:
        return False, "流水不存在"
    if log.invalid or log.revoke_status == "revoked":
        return False, CANNOT_UNDO_REASONS["already"]
    base_time = log.effective_time if hasattr(log, "effective_time") and log.effective_time else log.server_commit_ts or log.create_time
    if (datetime.now() - base_time) > timedelta(minutes=UNDO_WINDOW_MINUTES):
        return False, CANNOT_UNDO_REASONS["expired"]
    return True, ""


def undo_stock_log(db: Session, log_id: int, *, operator: str, ip: str = "") -> dict:
    log = db.query(StockLog).filter(StockLog.id == log_id).first()
    if not log:
        return {"ok": False, "msg": "流水不存在"}
    ok, why = can_undo(log)
    if not ok:
        return {"ok": False, "msg": why}

    m = db.query(Material).filter(Material.id == log.material_id).first()
    if not m:
        return {"ok": False, "msg": CANNOT_UNDO_REASONS["nomaterial"]}

    try:
        _apply_undo_for(db, log, m)
        log.invalid = 1
        log.revoke_status = "revoked"
        db.commit()
        return {"ok": True, "msg": "撤销成功", "log_id": log.id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "msg": f"撤销失败：{str(e)}"}


def _apply_undo_for(db: Session, log: StockLog, m: Material) -> StockLog:
    """按 log_type 反向作用"""
    lt = log.log_type
    if lt == "in":
        # 入库→撤销=出库（退这批入库）
        # 用原入库时的 num（正数）作为出库量
        out_num = log.num
        if out_num > m.stock_total_num:
            raise ValueError("库存不足，无法撤销入库")
        remain_num, remain_cost = calc_out_stock(
            old_num=m.stock_total_num,
            old_cost=m.stock_total_cost,
            out_num=out_num,
            avg_price=m.stock_avg_price,
        )
        m.stock_total_num = remain_num
        m.stock_total_cost = remain_cost
        db.flush()
        return db.add(StockLog(
            material_id=m.id, project_id=log.project_id,
            log_type="out_temp",
            num=-out_num, cost=-log.cost, avg_price=m.stock_avg_price,
            remark=f"[撤销#{log.id}] 入库撤销（反向补偿）",
            source=log.source, device_id=log.device_id,
        ))

    if lt in ("out_temp", "out_project"):
        # 出库→撤销=重新入库；log.num 是负数
        back_num = -log.num
        # 把原成本加回来
        new_num, new_cost, new_avg = calc_new_avg_price(
            old_num=m.stock_total_num, old_cost=m.stock_total_cost,
            add_num=back_num, add_cost=-log.cost,
        )
        m.stock_total_num = new_num
        m.stock_total_cost = new_cost
        m.stock_avg_price = new_avg
        db.flush()
        return db.add(StockLog(
            material_id=m.id, project_id=log.project_id,
            log_type="in",
            num=back_num, cost=-log.cost, avg_price=new_avg,
            remark=f"[撤销#{log.id}] {lt}撤销（反向补偿）",
            source=log.source, device_id=log.device_id,
        ))

    if lt == "lock":
        unlock_num = log.num   # 正数（锁定量）
        m.lock_num -= unlock_num
        if m.lock_num < 0:
            m.lock_num = 0.0
        db.flush()
        return db.add(StockLog(
            material_id=m.id, project_id=log.project_id,
            log_type="unlock",
            num=-unlock_num, cost=0.0, avg_price=m.stock_avg_price,
            remark=f"[撤销#{log.id}] 锁定撤销",
            source=log.source, device_id=log.device_id,
        ))

    if lt == "unlock":
        lock_num = -log.num   # 负数→正数
        # 加回锁定量，不超过可用库存
        usable = m.stock_total_num - m.lock_num
        if lock_num > usable:
            raise ValueError(f"锁定撤销失败：可用库存不足（当前可用 {usable}）")
        m.lock_num += lock_num
        db.flush()
        # 同步 project_bom 锁定量：如果原 log 有 project_id，找匹配 BOM（没 BOM 就跳过）
        if log.project_id:
            bom = db.query(ProjectBom).filter(
                ProjectBom.project_id == log.project_id,
                ProjectBom.material_id == log.material_id,
            ).first()
            if bom:
                bom.lock_num += lock_num
        return db.add(StockLog(
            material_id=m.id, project_id=log.project_id,
            log_type="lock",
            num=lock_num, cost=0.0, avg_price=m.stock_avg_price,
            remark=f"[撤销#{log.id}] 解锁撤销",
            source=log.source, device_id=log.device_id,
        ))

    raise ValueError(f"不支持撤销的流水类型: {lt}")
