# -*- coding: utf-8 -*-
"""冲突处理接口"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, principal_username
from core.response import success, fail
from core.ws_manager import ws_mgr
from models.conflict import Conflict
from schemas.conflict import ConflictResolveIn, ConflictBatchResolveIn

router = APIRouter()


def _conflict_to_dict(c: Conflict) -> dict:
    try:
        snaps = json.loads(c.snapshots_json or "[]")
    except Exception:
        snaps = []
    return {
        "id": c.id,
        "material_id": c.material_id,
        "stage_code": c.stage_code,
        "snapshots": snaps,
        "status": c.status,
        "chosen_source_index": c.chosen_source_index,
        "related_log_ids": c.related_log_ids or "",
        "operator": c.operator or "",
        "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S") if c.create_time else "",
        "update_time": c.update_time.strftime("%Y-%m-%d %H:%M:%S") if c.update_time else "",
    }


@router.get("/list")
def list_conflicts(
    status: str = "",
    material_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(Conflict)
    if status:
        q = q.filter(Conflict.status == status)
    if material_id:
        q = q.filter(Conflict.material_id == material_id)
    total = q.count()
    items = q.order_by(Conflict.update_time.desc(), Conflict.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return success({
        "total": total, "page": page, "page_size": page_size,
        "list": [_conflict_to_dict(c) for c in items],
        "pending_count": db.query(Conflict).filter(Conflict.status == "pending").count(),
    })


@router.post("/resolve/{conflict_id}")
async def resolve(
    conflict_id: int,
    data: ConflictResolveIn,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    c = db.query(Conflict).filter(Conflict.id == conflict_id).first()
    if not c:
        return fail("冲突不存在")
    if c.status in ("accepted", "dismissed"):
        return fail("冲突已处理，请勿重复操作")
    if data.status == "accepted":
        if data.chosen_snapshot_index is None:
            return fail("accepted 时必须指定 chosen_snapshot_index（生效快照下标）")
        try:
            snaps = json.loads(c.snapshots_json or "[]")
        except Exception:
            snaps = []
        if not (0 <= data.chosen_snapshot_index < len(snaps)):
            return fail("生效快照下标越界")
        c.status = "accepted"
        c.chosen_source_index = data.chosen_snapshot_index
        c.operator = principal_username(user)
    elif data.status == "dismissed":
        c.status = "dismissed"
        c.operator = principal_username(user)
    else:
        return fail("非法 status：accepted / dismissed")
    c.update_time = datetime.now()
    db.commit()
    await ws_mgr.notify_conflict_resolved(c.id, c.material_id, c.status)
    return success(_conflict_to_dict(c), "冲突处理成功")


@router.post("/resolve-batch")
async def resolve_batch(
    data: ConflictBatchResolveIn,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    ids = list({int(x) for x in data.ids})
    if not ids:
        return fail("未选择冲突")
    accepted_ids: list[int] = []
    mid_map: dict[int, int] = {}
    rows = db.query(Conflict).filter(Conflict.id.in_(ids)).all()
    for c in rows:
        if c.status in ("accepted", "dismissed"):
            continue
        if data.status == "accepted":
            idx = data.chosen_indexes.get(str(c.id))
            if idx is None:
                # 批量 accepted 时未传具体 index 默认取最新（最后一个快照）
                try:
                    snaps = json.loads(c.snapshots_json or "[]")
                except Exception:
                    snaps = []
                idx = max(0, len(snaps) - 1) if snaps else 0
            c.status = "accepted"
            c.chosen_source_index = int(idx)
        else:
            c.status = "dismissed"
        c.operator = principal_username(user)
        c.update_time = datetime.now()
        if c.status == "accepted":
            accepted_ids.append(c.id)
        mid_map[c.id] = c.material_id
    db.commit()
    mids = list(set(mid_map.values()))
    if accepted_ids:
        await ws_mgr.broadcast("conflict:resolved:batch", {
            "ids": accepted_ids, "material_ids": mids, "status": data.status,
        })
    return success({"processed": len(rows), "ids": [c.id for c in rows]}, "批量处理完成")


@router.post("/seed-demo")
def seed_demo(
    clear_first: bool = False,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """插入冲突演示测试数据（用于前端操作演示与截图）"""
    if clear_first:
        db.query(Conflict).delete()
        db.commit()

    now = datetime.now()

    def _ts(offset_min: int) -> str:
        return (now - timedelta(minutes=offset_min)).strftime("%Y-%m-%d %H:%M:%S")

    demo_rows = [
        # 1. 入库 vs 入库 冲突：APP +30 vs Web -15（场景：双方同时入库/出库同一物料）
        Conflict(
            material_id=1,
            stage_code=1001,
            snapshots_json=json.dumps([
                {
                    "source": "app",
                    "device": "HUAWEI-P60-0xA1",
                    "op_type": "stock_in",
                    "fixed_ts": _ts(12),
                    "local_device_ts": _ts(14),
                    "time_correction_flag": "ok",
                    "diff_fields": {"stock_total_num": 30, "stock_avg_price": 12.5},
                    "summary": "APP入库：M3x10 螺丝 30 颗，加权均价 12.5 元/颗（库存：原 20 → 50）",
                },
                {
                    "source": "web",
                    "device": "chrome-win11-pc01",
                    "op_type": "stock_out_temp",
                    "fixed_ts": _ts(10),
                    "local_device_ts": _ts(10),
                    "time_correction_flag": "ok",
                    "diff_fields": {"stock_total_num": -15},
                    "summary": "Web临时出库：M3x10 螺丝 15 颗（临时借出，未归还）（库存：原 20 → 5）",
                },
            ], ensure_ascii=False),
            status="pending",
            create_time=now - timedelta(minutes=8),
            update_time=now - timedelta(minutes=8),
        ),
        # 2. 物料编辑冲突：APP改规格 vs Web改备注
        Conflict(
            material_id=2,
            stage_code=1002,
            snapshots_json=json.dumps([
                {
                    "source": "app",
                    "device": "XIAOMI-13Pro-0xB2",
                    "op_type": "material_update",
                    "fixed_ts": _ts(38),
                    "local_device_ts": _ts(42),
                    "time_correction_flag": "forced",
                    "diff_fields": {"spec": "Φ8x30mm 镀锌", "warn_num": 20},
                    "summary": "APP编辑：外六角螺栓 规格改为『Φ8x30mm 镀锌』，告警阈值改为 20",
                },
                {
                    "source": "web",
                    "device": "edge-win10-pc02",
                    "op_type": "material_update",
                    "fixed_ts": _ts(35),
                    "local_device_ts": _ts(35),
                    "time_correction_flag": "ok",
                    "diff_fields": {"remark": "采购自五金商城A店，批次B20250812"},
                    "summary": "Web编辑：外六角螺栓 备注补充『采购自五金商城A店，批次B20250812』",
                },
            ], ensure_ascii=False),
            status="pending",
            create_time=now - timedelta(minutes=30),
            update_time=now - timedelta(minutes=30),
        ),
        # 3. BOM 锁定冲突：APP锁定 vs Web消耗
        Conflict(
            material_id=3,
            stage_code=1003,
            snapshots_json=json.dumps([
                {
                    "source": "app",
                    "device": "HUAWEI-P60-0xA1",
                    "op_type": "bom_lock",
                    "fixed_ts": _ts(65),
                    "local_device_ts": _ts(70),
                    "time_correction_flag": "forced",
                    "diff_fields": {"lock_num": 50, "project_id": 7, "project_name": "机器人底座装配"},
                    "summary": "APP BOM锁定：5mm 亚克力板 锁定 50 块（项目『机器人底座装配』）",
                },
                {
                    "source": "web",
                    "device": "chrome-win11-pc01",
                    "op_type": "stock_out_project",
                    "fixed_ts": _ts(60),
                    "local_device_ts": _ts(60),
                    "time_correction_flag": "ok",
                    "diff_fields": {"stock_total_num": -20, "project_id": 7},
                    "summary": "Web项目出库：5mm 亚克力板 出库 20 块（项目『机器人底座装配』）",
                },
            ], ensure_ascii=False),
            status="pending",
            create_time=now - timedelta(hours=1),
            update_time=now - timedelta(hours=1),
        ),
        # 4. 已处理（已生效）示例：优先Web
        Conflict(
            material_id=4,
            stage_code=1000,
            snapshots_json=json.dumps([
                {
                    "source": "app",
                    "device": "OPPO-FindX7-0xC3",
                    "op_type": "stock_in",
                    "fixed_ts": _ts(180),
                    "local_device_ts": _ts(190),
                    "time_correction_flag": "ok",
                    "diff_fields": {"stock_total_num": 10},
                    "summary": "APP入库：铜柱 M2x20 10 颗",
                },
                {
                    "source": "web",
                    "device": "chrome-win11-pc01",
                    "op_type": "stock_in",
                    "fixed_ts": _ts(175),
                    "local_device_ts": _ts(175),
                    "time_correction_flag": "ok",
                    "diff_fields": {"stock_total_num": 100, "stock_avg_price": 0.8},
                    "summary": "Web入库：铜柱 M2x20 100 颗，均价 0.8 元/颗",
                },
            ], ensure_ascii=False),
            status="accepted",
            chosen_source_index=1,
            operator="admin",
            create_time=now - timedelta(hours=3),
            update_time=now - timedelta(hours=2),
        ),
        # 5. 已放弃示例
        Conflict(
            material_id=5,
            stage_code=998,
            snapshots_json=json.dumps([
                {
                    "source": "app",
                    "device": "VIVO-X100-0xD4",
                    "op_type": "material_create",
                    "fixed_ts": _ts(300),
                    "local_device_ts": _ts(320),
                    "time_correction_flag": "forced",
                    "diff_fields": {"name": "测试草稿物料-勿用", "spec": "草稿"},
                    "summary": "APP创建物料：草稿（测试）",
                },
            ], ensure_ascii=False),
            status="dismissed",
            operator="admin",
            create_time=now - timedelta(hours=5),
            update_time=now - timedelta(hours=4, minutes=50),
        ),
    ]

    for row in demo_rows:
        db.add(row)
    db.commit()
    return success({"inserted": len(demo_rows)}, "冲突演示数据插入完成，可刷新前端冲突处理页查看")
