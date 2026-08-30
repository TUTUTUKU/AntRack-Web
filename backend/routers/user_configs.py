# -*- coding: utf-8 -*-
"""用户配置：Web-APP 双向同步，服务端一张配置表"""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, principal_username
from core.response import success
from core.ws_manager import ws_mgr
from models.user_config import UserConfig
from schemas.user_config import ConfigBatchSetIn

router = APIRouter()


def _fmt_time(t):
    return t.strftime("%Y-%m-%d %H:%M:%S") if t else ""


@router.get("/all")
def all_config(db: Session = Depends(get_db), user: object = Depends(get_current_user)):
    rows = db.query(UserConfig).filter(UserConfig.username == principal_username(user)).all()
    return success({r.key: r.value for r in rows})


@router.get("/list")
def list_config(db: Session = Depends(get_db), user: object = Depends(get_current_user)):
    rows = db.query(UserConfig).filter(UserConfig.username == principal_username(user)).order_by(UserConfig.key).all()
    return success([
        {"key": r.key, "value": r.value, "update_time": _fmt_time(r.update_time)}
        for r in rows
    ])


@router.post("/set")
async def set_config(data: dict, db: Session = Depends(get_db), user: object = Depends(get_current_user)):
    """单条或批量 dict 写入：{ "key": "xxx", "value": "yyy" } 或 { k1: v1, k2: v2 }"""
    if "key" in data:
        items = {data["key"]: data.get("value", "")}
    else:
        items = {k: v for k, v in data.items() if isinstance(k, str)}
    return await _apply_batch(db, principal_username(user), items)


@router.post("/batch")
async def batch_set(data: ConfigBatchSetIn, db: Session = Depends(get_db), user: object = Depends(get_current_user)):
    return await _apply_batch(db, principal_username(user), data.items)


async def _apply_batch(db: Session, user: str, items: dict):
    changed = False
    for k, v in items.items():
        if not isinstance(k, str) or not k:
            continue
        row = db.query(UserConfig).filter(UserConfig.username == user, UserConfig.key == k).first()
        if row:
            if row.value != str(v):
                row.value = str(v)
                row.update_time = datetime.now()
                changed = True
        else:
            db.add(UserConfig(username=user, key=k, value=str(v)))
            changed = True
    db.commit()
    if changed:
        await ws_mgr.broadcast("config:changed", {"by": user, "keys": list(items.keys())})
    return success({"changed": changed, "updated_keys": list(items.keys())}, "保存成功")
