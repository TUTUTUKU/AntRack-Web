# -*- coding: utf-8 -*-
"""冲突处理接口"""
from __future__ import annotations
import json
from datetime import datetime
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
