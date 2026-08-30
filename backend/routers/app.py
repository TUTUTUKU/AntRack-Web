# -*- coding: utf-8 -*-
"""App 端接口：激活、心跳、握手、离线同步。

设计要点：
- 激活真实性由 App 保证（activation_proof 非空即接受），服务器不算激活码
- device_token 是 30 天有效的 JWT，type=device
- 同步接口必须幂等：相同 idempotency_key 重复提交只生效一次
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import DEFAULT_ADMIN_USERNAME
from core.response import success, fail
from core.security import create_device_token, decode_token, DEVICE_TOKEN_EXPIRE_DAYS
from core.version_util import get_app_version
from core.biz_common import (
    parse_iso_dt, fmt_dt, get_global_check_code, bump_global_check_code, check_idempotency,
)
from core.stock_calc import calc_new_avg_price, calc_out_stock
from core.op_log_service import write_op_log
from core.ws_manager import ws_mgr
from database import get_db, SessionLocal
from dependencies import get_current_user, Principal
from models.conflict import Conflict
from models.material import Material
from models.stock_log import StockLog
from models.project_bom import ProjectBom
from models.project import Project
from models.backup_snapshot import BackupSnapshot
from schemas.app_sync import OfflineSyncIn, OpResult

router = APIRouter()


class ActivateIn(BaseModel):
    device_id: str = Field(..., min_length=1, description="设备唯一标识（App 自行生成，如安卓 Android ID）")
    device_name: str = Field("", description="设备名称（如 vivo X100）")
    activation_proof: str = Field(..., min_length=1, description="App 本地激活凭证（非空即接受，服务器不做激活码计算）")


class HeartbeatIn(BaseModel):
    device_token: str = Field(..., description="当前持有的设备令牌")


# ===== 激活 / 心跳 / 状态 =====

@router.post("/activate")
def activate(data: ActivateIn):
    token, expires_at = create_device_token(
        device_id=data.device_id.strip(),
        device_name=data.device_name.strip(),
    )
    return success({
        "device_token": token,
        "expires_at": expires_at,
        "valid_days": DEVICE_TOKEN_EXPIRE_DAYS,
    }, "设备激活成功")


@router.post("/heartbeat")
def heartbeat(data: HeartbeatIn, db: Session = Depends(get_db)):
    """周期心跳：验证 token、返回阶段号和最新备份元数据。"""
    payload = decode_token(data.device_token)
    if not payload:
        return fail("设备令牌无效或已过期，请重新激活", data={"valid": False})
    if payload.get("type") != "device":
        return fail("令牌类型不正确", data={"valid": False})
    exp = payload.get("exp")
    if not exp:
        return fail("令牌格式异常", data={"valid": False})
    remaining_seconds = exp - datetime.utcnow().timestamp()
    if remaining_seconds <= 0:
        return fail("设备令牌已过期，请重新激活", data={"valid": False})

    code = get_global_check_code(db)
    latest_snap = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).first()
    snap_meta = {}
    if latest_snap:
        ver = f"{latest_snap.version_x}.{latest_snap.version_y}.{latest_snap.version_z}"
        snap_meta = {
            "id": latest_snap.id,
            "create_time": fmt_dt(latest_snap.create_time),
            "version": ver,
            "file_size": latest_snap.file_size or 0,
            "trigger": latest_snap.trigger,
        }
    pending_conflicts = db.query(Conflict).filter(Conflict.status == "pending").count()
    return success({
        "valid": True,
        "expires_at": datetime.utcfromtimestamp(exp).isoformat(),
        "remaining_days": round(remaining_seconds / 86400, 1),
        "version": get_app_version(),
        "global_check_code": code,
        "server_time": fmt_dt(datetime.now()),
        "latest_backup_meta": snap_meta,
        "pending_conflict_count": pending_conflicts,
    }, "设备激活态有效")


@router.get("/status")
def status_check(principal: object = Depends(get_current_user)):
    """管理员 token 或设备 token 均可调用的鉴权检查。"""
    if isinstance(principal, Principal):
        return success({"type": "device", "device_id": principal.device_id}, "设备令牌有效")
    return success({"type": "user", "username": principal.username}, "管理员令牌有效")


# ===== 握手接口：APP 联网先调用一次 =====

@router.get("/handshake")
def handshake(
    last_check_code: int = Query(0, description="APP 上一次记录的 global_check_code；0=首次"),
    db: Session = Depends(get_db),
    principal: object = Depends(get_current_user),
):
    """返回当前阶段号、服务端时间（用于时间偏移）、最新备份元数据、阶段是否变化、版本。"""
    current = get_global_check_code(db)
    latest_snap = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).first()
    snap_meta = {}
    if latest_snap:
        ver = f"{latest_snap.version_x}.{latest_snap.version_y}.{latest_snap.version_z}"
        snap_meta = {
            "id": latest_snap.id,
            "create_time": fmt_dt(latest_snap.create_time),
            "version": ver,
            "file_size": latest_snap.file_size or 0,
            "trigger": latest_snap.trigger,
        }
    pending = db.query(Conflict).filter(Conflict.status == "pending").count()
    return success({
        "current_global_check_code": current,
        "current_server_time": fmt_dt(datetime.now()),
        "version": get_app_version(),
        "stage_changed_since_last": (last_check_code > 0) and (last_check_code != current),
        "latest_backup_meta": snap_meta,
        "pending_conflict_count": pending,
    })


# ===== 离线同步批量上传 =====

def _apply_time_correction(local_dt: datetime | None, snapshot_dt: datetime, current_dt: datetime) -> tuple[datetime, str]:
    """时间偏移补偿：local_dt + (current_dt - snapshot_dt) 把设备时间映射到服务端时间轴，
    落点超出 [snapshot_dt, current_dt] 区间则强制用当前时间。"""
    if local_dt is None:
        return current_dt, "forced"
    try:
        delta = current_dt - snapshot_dt
        fixed = local_dt + delta
    except Exception:
        return current_dt, "forced"
    lo = min(snapshot_dt, current_dt)
    hi = max(snapshot_dt, current_dt)
    if lo <= fixed <= hi:
        return fixed, "ok"
    return current_dt, "forced"


def _pick_device_id(principal: object) -> str:
    if isinstance(principal, Principal):
        return principal.device_id or ""
    return ""


def _pick_username(principal: object) -> str:
    if isinstance(principal, Principal):
        return "app"
    try:
        return getattr(principal, "username", "") or DEFAULT_ADMIN_USERNAME
    except Exception:
        return DEFAULT_ADMIN_USERNAME


@router.post("/offline-sync")
async def offline_sync(
    data: OfflineSyncIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: object = Depends(get_current_user),
):
    """离线同步：阶段号不一致触发冲突，逐条幂等落库并写操作日志。"""
    client_ip = request.client.host if request.client else ""
    device_id = _pick_device_id(principal)
    username = _pick_username(principal)

    snapshot_stage = int(data.snapshot_global_check_code or 0)
    snapshot_server_dt = parse_iso_dt(data.snapshot_server_time) or datetime.now()
    current_stage = get_global_check_code(db)
    current_server_dt = datetime.now()

    stage_mismatch = snapshot_stage != current_stage

    results: list[OpResult] = []
    conflict_map: dict[int, list[dict]] = {}   # material_id -> list[snapshots]
    triggered_conflict_ids: list[int] = []

    # 按 ops 顺序执行（业务可能有依赖）
    for op in data.ops:
        key = (op.idempotency_key or "").strip()
        res = OpResult(
            idempotency_key=key,
            ok=False,
            error="",
        )
        # 幂等检查（整条离线同步事务内也去重）
        existing = check_idempotency(db, key)
        if existing:
            res.ok = True
            res.log_id = existing.id
            res.time_correction_flag = existing.time_correction_flag or ""
            res.fixed_ts = fmt_dt(existing.server_commit_ts)
            results.append(res)
            continue

        local_dt = parse_iso_dt(op.local_device_ts)
        fixed_dt, flag = _apply_time_correction(local_dt, snapshot_server_dt, current_server_dt)
        res.time_correction_flag = flag
        res.fixed_ts = fmt_dt(fixed_dt)

        try:
            log_id, mid, summary = _apply_op(db, op, fixed_dt, device_id)
        except Exception as e:
            res.error = str(e)
            results.append(res)
            # 失败操作不参与冲突合并
            continue

        # 回写幂等键、时间校正字段、来源
        if log_id is not None:
            log = db.query(StockLog).filter(StockLog.id == log_id).first()
            if log:
                log.client_op_idempotency_key = key
                log.local_device_ts = local_dt
                log.time_correction_flag = flag
                log.server_commit_ts = fixed_dt
                log.source = "app"
                log.device_id = device_id or ""
                db.flush()

        res.ok = True
        res.log_id = log_id
        results.append(res)

        # 阶段不一致 → 产生冲突快照（按物料合并）
        if stage_mismatch and mid is not None:
            snap = {
                "source": "app",
                "device": device_id or "",
                "op_type": op.op_type,
                "fixed_ts": fmt_dt(fixed_dt),
                "local_device_ts": op.local_device_ts or "",
                "time_correction_flag": flag,
                "payload": op.payload,
                "summary": summary,
            }
            conflict_map.setdefault(mid, []).append(snap)

        try:
            write_op_log(
                db,
                username=username,
                source="app",
                device_id=device_id or "",
                action=op.op_type,
                material_id=mid,
                related_log_id=log_id,
                detail={**(op.payload or {}), "summary": summary},
                ip=client_ip,
                effective_time=fixed_dt,
            )
        except Exception:
            pass

    # 提交冲突记录（按物料合并）
    if conflict_map:
        new_ids: list[int] = []
        mids: list[int] = []
        for mid, snaps in conflict_map.items():
            # 同阶段同物料的 pending 冲突追加合并；否则新建
            c = db.query(Conflict).filter(
                Conflict.material_id == mid,
                Conflict.stage_code == snapshot_stage,
                Conflict.status == "pending",
            ).first()
            if c:
                try:
                    arr = json.loads(c.snapshots_json or "[]")
                except Exception:
                    arr = []
                arr.extend(snaps)
                c.snapshots_json = json.dumps(arr, ensure_ascii=False)
                c.update_time = datetime.now()
            else:
                c = Conflict(
                    material_id=mid,
                    stage_code=snapshot_stage,
                    snapshots_json=json.dumps(snaps, ensure_ascii=False),
                    status="pending",
                )
                db.add(c)
            db.flush()
            db.refresh(c)
            new_ids.append(c.id)
            mids.append(mid)
            triggered_conflict_ids.append(c.id)
        db.commit()
        await ws_mgr.notify_conflict_created(new_ids, list(set(mids)))
    else:
        db.commit()

    for r in results:
        for cid in triggered_conflict_ids:
            r.triggered_conflict_id = cid
            break

    return success({
        "results": [r.model_dump() for r in results],
        "current_global_check_code": get_global_check_code(db),
        "current_server_time": fmt_dt(datetime.now()),
        "stage_mismatch": stage_mismatch,
        "triggered_conflict_ids": triggered_conflict_ids,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "conflicts": len(triggered_conflict_ids),
        },
    })


# ===== OP 执行：把离线操作映射到业务流水 =====
# 支持：stock_in / stock_out_temp / material_create / material_update /
# bom_lock / bom_unlock / project_create

def _apply_op(
    db: Session, op, fixed_dt: datetime, device_id: str,
) -> tuple[int | None, int | None, str]:
    """返回 (stock_log_id or None, material_id or None, summary)"""
    t = op.op_type
    p = op.payload or {}

    if t == "stock_in":
        mid = int(p.get("material_id") or 0)
        in_num = float(p.get("in_num") or 0)
        pay_total = float(p.get("pay_total") or 0)
        remark = str(p.get("remark") or "")
        if in_num <= 0:
            raise ValueError("入库数量必须大于 0")
        if pay_total < 0:
            raise ValueError("实付总价不能为负")
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise ValueError("物料不存在")
        new_num, new_cost, new_avg = calc_new_avg_price(
            old_num=m.stock_total_num, old_cost=m.stock_total_cost,
            add_num=in_num, add_cost=pay_total,
        )
        m.stock_total_num = new_num
        m.stock_total_cost = new_cost
        m.stock_avg_price = new_avg
        m.server_commit_ts = fixed_dt
        log = StockLog(
            material_id=mid, project_id=None,
            log_type="in",
            num=in_num, cost=pay_total, avg_price=new_avg,
            remark=remark or "APP 离线入库",
            create_time=fixed_dt, server_commit_ts=fixed_dt,
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        return log.id, mid, f"入库 {in_num}，总价 {pay_total}"

    if t == "stock_out_temp":
        mid = int(p.get("material_id") or 0)
        out_num = float(p.get("out_num") or 0)
        remark = str(p.get("remark") or "")
        if out_num <= 0:
            raise ValueError("出库数量必须大于 0")
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise ValueError("物料不存在")
        if out_num > m.stock_total_num:
            raise ValueError(f"出库数量超出实际库存（当前 {int(round(m.stock_total_num))}）")
        remain_num, remain_cost = calc_out_stock(
            old_num=m.stock_total_num, old_cost=m.stock_total_cost,
            out_num=out_num, avg_price=m.stock_avg_price,
        )
        m.stock_total_num = remain_num
        m.stock_total_cost = remain_cost
        m.server_commit_ts = fixed_dt
        log = StockLog(
            material_id=mid, project_id=None,
            log_type="out_temp",
            num=-out_num,
            cost=round(out_num * m.stock_avg_price, 6),
            avg_price=m.stock_avg_price,
            remark=remark or "APP 离线临时出库",
            create_time=fixed_dt, server_commit_ts=fixed_dt,
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        return log.id, mid, f"临时出库 {out_num}"

    if t == "material_create":
        cat_id = int(p.get("category_id") or 0)
        name = str(p.get("name") or "").strip()
        if not name:
            raise ValueError("物料名称不能为空")
        init_num = float(p.get("init_stock") or 0)
        init_price = float(p.get("init_cost") or 0)
        init_cost_total = round(init_num * init_price, 6)
        m = Material(
            name=name, category_id=cat_id,
            code=str(p.get("code") or "").strip(),
            spec=str(p.get("spec") or ""),
            unit=str(p.get("unit") or "个").strip() or "个",
            price_unit=str(p.get("price_unit") or "¥").strip() or "¥",
            image=str(p.get("image") or ""),
            warn_num=float(p.get("warn_num") or 0),
            remark=str(p.get("remark") or ""),
            stock_total_num=init_num,
            stock_total_cost=init_cost_total,
            stock_avg_price=(init_price if init_num > 0 else 0.0),
            server_commit_ts=fixed_dt,
        )
        db.add(m)
        db.flush()
        db.refresh(m)
        log_id = None
        if init_num > 0:
            log = StockLog(
                material_id=m.id, project_id=None,
                log_type="in",
                num=init_num, cost=init_cost_total,
                avg_price=m.stock_avg_price,
                remark="APP 离线物料创建初始入库",
                create_time=fixed_dt, server_commit_ts=fixed_dt,
            )
            db.add(log)
            db.flush()
            db.refresh(log)
            log_id = log.id
        return log_id, m.id, f"创建物料「{name}」，初始库存 {init_num}"

    if t == "material_update":
        mid = int(p.get("material_id") or 0)
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise ValueError("物料不存在")
        for k in ("name", "code", "spec", "unit", "price_unit", "image", "remark"):
            if k in p and p[k] is not None:
                setattr(m, k, p[k])
        if "category_id" in p and p["category_id"]:
            m.category_id = int(p["category_id"])
        if "warn_num" in p:
            m.warn_num = float(p["warn_num"] or 0)
        m.server_commit_ts = fixed_dt
        return None, mid, "更新物料基础信息"

    if t == "bom_lock":
        mid = int(p.get("material_id") or 0)
        pid = int(p.get("project_id") or 0)
        lock_num = float(p.get("lock_num") or 0)
        if lock_num <= 0:
            raise ValueError("锁定数量必须大于 0")
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise ValueError("物料不存在")
        usable = m.stock_total_num - m.lock_num
        if lock_num > usable:
            raise ValueError(f"锁定数量超出可用库存（当前可用 {int(round(usable))}）")
        m.lock_num += lock_num
        m.server_commit_ts = fixed_dt
        log = StockLog(
            material_id=mid, project_id=pid or None,
            log_type="lock",
            num=lock_num, cost=0.0, avg_price=m.stock_avg_price,
            remark="APP 离线 BOM 锁定",
            create_time=fixed_dt, server_commit_ts=fixed_dt,
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        if pid:
            bom = db.query(ProjectBom).filter(
                ProjectBom.project_id == pid,
                ProjectBom.material_id == mid,
            ).first()
            if bom:
                bom.lock_num = (bom.lock_num or 0) + lock_num
        return log.id, mid, f"BOM 锁定 {lock_num}"

    if t == "bom_unlock":
        mid = int(p.get("material_id") or 0)
        pid = int(p.get("project_id") or 0)
        unlock_num = float(p.get("unlock_num") or 0)
        if unlock_num <= 0:
            raise ValueError("解锁数量必须大于 0")
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise ValueError("物料不存在")
        if unlock_num > m.lock_num:
            raise ValueError(f"解锁数量超出已锁定量（当前锁定 {int(round(m.lock_num))}）")
        m.lock_num -= unlock_num
        m.server_commit_ts = fixed_dt
        log = StockLog(
            material_id=mid, project_id=pid or None,
            log_type="unlock",
            num=-unlock_num, cost=0.0, avg_price=m.stock_avg_price,
            remark="APP 离线 BOM 解锁",
            create_time=fixed_dt, server_commit_ts=fixed_dt,
        )
        db.add(log)
        db.flush()
        db.refresh(log)
        if pid:
            bom = db.query(ProjectBom).filter(
                ProjectBom.project_id == pid,
                ProjectBom.material_id == mid,
            ).first()
            if bom:
                bom.lock_num = max(0.0, (bom.lock_num or 0) - unlock_num)
        return log.id, mid, f"BOM 解锁 {unlock_num}"

    if t == "project_create":
        name = str(p.get("name") or "").strip()
        if not name:
            raise ValueError("项目名称不能为空")
        pj = Project(
            name=name,
            description=str(p.get("description") or ""),
            status=str(p.get("status") or "planning"),
        )
        db.add(pj)
        db.flush()
        db.refresh(pj)
        return None, None, f"创建项目「{name}」"

    raise ValueError(f"暂不支持的离线操作类型：{t}")
