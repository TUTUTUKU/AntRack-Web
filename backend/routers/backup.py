# -*- coding: utf-8 -*-
"""数据备份与恢复：手动/自动/APP 触发生成快照，支持跨版本字段自动过滤和恢复后广播。"""
from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timedelta
from typing import Any, Dict, List
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import STATIC_DIR, STATIC_URL_PREFIX, BASE_DIR
from core.response import success, fail
from core.version_util import get_app_version, parse_version
from core.ws_manager import ws_mgr
from core.biz_common import bump_global_check_code
from database import get_db
from dependencies import get_current_user, principal_username, is_admin_user
from models.backup_snapshot import BackupSnapshot
from models.user import User
from models.category import Category
from models.material import Material
from models.project import Project
from models.project_bom import ProjectBom
from models.stock_log import StockLog

router = APIRouter()

SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
TABLE_FILES = {
    "categories": "categories.json",
    "materials": "materials.json",
    "projects": "projects.json",
    "project_boms": "project_boms.json",
    "stock_logs": "stock_logs.json",
}
STATIC_PREFIX = "static/"
_SNAPSHOT_SUBDIR = "data/backups"


# ========= 公共工具 =========

def _row_to_dict(row: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in row.__table__.columns:
        v = getattr(row, c.name)
        if isinstance(v, datetime):
            out[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            out[c.name] = v
    return out


def _strip_static_prefix(url: str) -> str:
    if not url:
        return ""
    p = url.strip().lstrip("/")
    if p.startswith(STATIC_PREFIX):
        p = p[len(STATIC_PREFIX):]
    return p


def _collect_image_names(materials: List[Dict[str, Any]]) -> List[str]:
    seen = []
    for m in materials:
        name = _strip_static_prefix(m.get("image") or "")
        if name and name not in seen:
            seen.append(name)
    return seen


def _build_zip_bytes(db: Session) -> tuple[bytes, dict]:
    """把当前数据库打包成 ZIP 字节串，返回 (bytes, manifest_dict)。"""
    categories = [_row_to_dict(r) for r in db.query(Category).all()]
    materials = [_row_to_dict(r) for r in db.query(Material).all()]
    projects = [_row_to_dict(r) for r in db.query(Project).all()]
    project_boms = [_row_to_dict(r) for r in db.query(ProjectBom).all()]
    stock_logs = [_row_to_dict(r) for r in db.query(StockLog).all()]
    ver = get_app_version()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "system_version": ver,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": "AntRack",
        "counts": {
            "categories": len(categories),
            "materials": len(materials),
            "projects": len(projects),
            "project_boms": len(project_boms),
            "stock_logs": len(stock_logs),
        },
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(TABLE_FILES["categories"], json.dumps(categories, ensure_ascii=False))
        zf.writestr(TABLE_FILES["materials"], json.dumps(materials, ensure_ascii=False))
        zf.writestr(TABLE_FILES["projects"], json.dumps(projects, ensure_ascii=False))
        zf.writestr(TABLE_FILES["project_boms"], json.dumps(project_boms, ensure_ascii=False))
        zf.writestr(TABLE_FILES["stock_logs"], json.dumps(stock_logs, ensure_ascii=False))
        static_root = str(STATIC_DIR)
        for img_name in _collect_image_names(materials):
            abs_path = os.path.join(static_root, img_name)
            if os.path.isfile(abs_path):
                zf.write(abs_path, arcname=STATIC_PREFIX + img_name)
    buf.seek(0)
    return buf.getvalue(), manifest


def _gen_full_backup_zip(db: Session, *, trigger: str = "manual", note: str = "") -> dict:
    """生成备份文件落盘到 data/backups/ 下，写入备份表。
    只 INSERT snapshot 行并 flush，不 commit（由调用方决定提交时机）。"""
    data_bytes, manifest = _build_zip_bytes(db)
    ver = parse_version(manifest.get("system_version", "0.0.0"))

    dir_path = BASE_DIR / _SNAPSHOT_SUBDIR
    dir_path.mkdir(parents=True, exist_ok=True)
    src = "app" if "app" in trigger else "web"
    file_size = len(data_bytes)

    snap = BackupSnapshot(
        trigger=trigger,
        version_x=ver[0], version_y=ver[1], version_z=ver[2],
        file_path="",
        file_size=file_size,
        note=note or "",
    )
    db.add(snap)
    db.flush()
    db.refresh(snap)

    filename = f"{src}_{snap.id:04d}.ans"
    rel_path = f"{_SNAPSHOT_SUBDIR}/{filename}"
    full_path = BASE_DIR / rel_path
    full_path.write_bytes(data_bytes)

    snap.file_path = rel_path
    db.flush()
    return {
        "snapshot_id": snap.id,
        "relative_path": rel_path,
        "file_size": file_size,
        "exported_at": manifest["exported_at"],
        "version": manifest.get("system_version", get_app_version()),
    }


def _snap_out(s: BackupSnapshot) -> dict:
    ver = f"{s.version_x}.{s.version_y}.{s.version_z}"
    src = "APP" if "app" in (s.trigger or "") else "WEB"
    return {
        "id": s.id,
        "name": f"{src}#{s.id}",
        "trigger": s.trigger,
        "version": ver,
        "file_path": s.file_path or "",
        "file_size": s.file_size or 0,
        "note": s.note or "",
        "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S") if s.create_time else "",
        "expiry_time": s.expiry_time.strftime("%Y-%m-%d %H:%M:%S") if s.expiry_time else "",
    }


# ========= 路由 =========

@router.get("/list")
def list_snapshots(
    page: int = 1,
    page_size: int = 20,
    trigger: str = "",
    trigger_type: str = "",
    source: str = "",
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """列表支持两个维度筛选：
    - trigger_type: manual（手动）/ auto（自动）
    - source: web / app（按备份文件名前缀区分来源）
    兼容旧的 trigger 精确匹配参数。
    """
    q = db.query(BackupSnapshot)
    if trigger:
        q = q.filter(BackupSnapshot.trigger == trigger)
    if trigger_type == "manual":
        q = q.filter(BackupSnapshot.trigger.in_(["manual", "app_manual"]))
    elif trigger_type == "auto":
        q = q.filter(BackupSnapshot.trigger.in_(["auto", "weekly", "after_proofread"]))
    if source == "web":
        q = q.filter(~BackupSnapshot.trigger.like("app%"))
    elif source == "app":
        q = q.filter(BackupSnapshot.trigger.like("app%"))
    total = q.count()
    items = q.order_by(BackupSnapshot.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return success({
        "total": total, "page": page, "page_size": page_size,
        "list": [_snap_out(s) for s in items],
    })


@router.get("/latest-meta")
def latest_snapshot_meta(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    s = db.query(BackupSnapshot).order_by(BackupSnapshot.id.desc()).first()
    if not s:
        return success({})
    return success(_snap_out(s))


@router.get("/export")
def export_backup(
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """一键下载 .ans 备份（同时落盘并写快照表）。"""
    if not is_admin_user(user):
        return fail("仅管理员可执行备份操作", code=403)
    try:
        info = _gen_full_backup_zip(db, trigger="manual", note=f"管理员 {principal_username(user)} 手动下载")
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"生成备份失败：{e}")

    full_path = BASE_DIR / info["relative_path"]
    data_bytes = full_path.read_bytes()
    filename = full_path.name
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        io.BytesIO(data_bytes),
        media_type="application/zip",
        headers=headers,
    )


@router.post("/create")
def create_snapshot(
    trigger: str = "manual",
    note: str = "",
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """APP / Web 手动生成快照（仅落盘到服务端，不下载）。"""
    try:
        suffix = note or f"by {principal_username(user)}"
        info = _gen_full_backup_zip(db, trigger=trigger, note=suffix)
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"生成备份失败：{e}")
    s = db.query(BackupSnapshot).filter(BackupSnapshot.id == info["snapshot_id"]).first()
    return success(_snap_out(s), "快照生成成功")


@router.get("/download/{snapshot_id}")
def download_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    s = db.query(BackupSnapshot).filter(BackupSnapshot.id == snapshot_id).first()
    if not s:
        return fail("快照不存在")
    full = Path(s.file_path) if os.path.isabs(s.file_path) else (BASE_DIR / s.file_path)
    if not full.exists():
        return fail("快照文件不存在（可能已被清理）")
    headers = {"Content-Disposition": f'attachment; filename="{full.name}"'}
    return StreamingResponse(
        io.BytesIO(full.read_bytes()),
        media_type="application/zip",
        headers=headers,
    )


@router.delete("/delete/{snapshot_id}")
def delete_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    s = db.query(BackupSnapshot).filter(BackupSnapshot.id == snapshot_id).first()
    if not s:
        return fail("快照不存在")
    full = Path(s.file_path) if os.path.isabs(s.file_path) else (BASE_DIR / s.file_path)
    try:
        if full.exists():
            full.unlink()
    except Exception:
        pass
    db.delete(s)
    db.commit()
    return success(msg="快照已删除")


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """上传 .ans 恢复（跨版本字段自动过滤，主版本不同也允许恢复）。"""
    if not is_admin_user(user):
        return fail("仅管理员可执行恢复操作", code=403)

    raw_name = (file.filename or "").lower()
    if not raw_name.endswith(".ans") and not raw_name.endswith(".zip"):
        return fail("备份文件格式不正确，请上传 .ans 文件")
    content = await file.read()
    if not content:
        return fail("备份文件为空")
    if len(content) > 200 * 1024 * 1024:
        return fail("备份文件过大（>200MB）")

    try:
        zf = zipfile.ZipFile(io.BytesIO(content), "r")
    except zipfile.BadZipFile:
        return fail("备份文件已损坏或不是有效的 ZIP")

    names = set(zf.namelist())
    if MANIFEST_NAME not in names:
        return fail("备份缺少 manifest.json，无法识别格式")
    try:
        manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
    except Exception:
        return fail("manifest.json 解析失败")
    sv = int(manifest.get("schema_version", 0))
    if sv > SCHEMA_VERSION:
        return fail(f"备份 schema={sv} 高于当前系统 {SCHEMA_VERSION}，请先升级系统")

    try:
        data = {
            key: json.loads(zf.read(fname).decode("utf-8"))
            for key, fname in TABLE_FILES.items()
            if fname in names
        }
    except Exception as e:
        return fail(f"备份 JSON 解析失败：{e}")
    for key in TABLE_FILES:
        if key not in data:
            return fail(f"备份不完整，缺少 {key}.json")

    # 跨版本字段过滤：只保留当前系统模型里存在的列
    current_ver = parse_version(get_app_version())
    snap_ver = parse_version(str(manifest.get("system_version", "0.0.0")))
    major_mismatch = snap_ver[0] != current_ver[0]

    def filter_rows(rows, model_cls):
        cols = {c.name for c in model_cls.__table__.columns}
        out = []
        for row in rows:
            out.append({k: v for k, v in row.items() if k in cols})
        return out

    filtered = {
        "categories": filter_rows(data["categories"], Category),
        "materials": filter_rows(data["materials"], Material),
        "projects": filter_rows(data["projects"], Project),
        "project_boms": filter_rows(data["project_boms"], ProjectBom),
        "stock_logs": filter_rows(data["stock_logs"], StockLog),
    }

    conn = db.connection().connection
    restored_imgs = 0
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM stock_log")
        conn.execute("DELETE FROM project_bom")
        conn.execute("DELETE FROM project")
        conn.execute("DELETE FROM material")
        conn.execute("DELETE FROM category")
        # 同步清空依赖业务数据的关联表，避免和恢复的主键冲突
        conn.execute("DELETE FROM conflict")
        conn.execute("DELETE FROM operation_log")
        conn.execute("PRAGMA foreign_keys=ON")

        _bulk_insert(conn, "category", filtered["categories"], Category)
        _bulk_insert(conn, "material", filtered["materials"], Material)
        _bulk_insert(conn, "project", filtered["projects"], Project)
        _bulk_insert(conn, "project_bom", filtered["project_boms"], ProjectBom)
        _bulk_insert(conn, "stock_log", filtered["stock_logs"], StockLog)

        static_root = str(STATIC_DIR)
        os.makedirs(static_root, exist_ok=True)
        for img_name in _collect_image_names(filtered["materials"]):
            arc = STATIC_PREFIX + img_name
            if arc in names:
                img_bytes = zf.read(arc)
                dest = os.path.join(static_root, img_name)
                # 路径穿越防护：只允许写入静态资源根目录下
                if os.path.commonpath([os.path.abspath(dest), os.path.abspath(static_root)]) != os.path.abspath(static_root):
                    continue
                with open(dest, "wb") as f:
                    f.write(img_bytes)
                restored_imgs += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        try: conn.execute("PRAGMA foreign_keys=ON")
        except Exception: pass
        return fail(f"恢复失败，已全部回滚：{e}")

    db.expire_all()
    # 恢复属于批量数据集变更，阶段号 +1 并广播通知其他客户端拉最新
    bump_global_check_code(db)
    db.commit()
    await ws_mgr.notify_restored(None, manifest.get("system_version", ""))

    return success(
        {
            "stats": {
                "categories": len(filtered["categories"]),
                "materials": len(filtered["materials"]),
                "projects": len(filtered["projects"]),
                "project_boms": len(filtered["project_boms"]),
                "stock_logs": len(filtered["stock_logs"]),
                "images": restored_imgs,
            },
            "exported_at": manifest.get("exported_at", ""),
            "snapshot_system_version": manifest.get("system_version", ""),
            "current_version": get_app_version(),
            "major_mismatch": major_mismatch,
            "dropped_fields_note": "主版本不一致或字段多于当前系统的部分已自动过滤（仅导入当前系统存在字段）" if major_mismatch else "",
        },
        "恢复成功" + ("（已按当前系统字段过滤跨版本兼容恢复）" if major_mismatch else ""),
    )


@router.post("/restore-from-snapshot/{snapshot_id}")
async def restore_from_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """从服务端已保存的快照直接恢复。"""
    if not is_admin_user(user):
        return fail("仅管理员可执行恢复操作", code=403)
    s = db.query(BackupSnapshot).filter(BackupSnapshot.id == snapshot_id).first()
    if not s:
        return fail("快照不存在")
    full = Path(s.file_path) if os.path.isabs(s.file_path) else (BASE_DIR / s.file_path)
    if not full.exists():
        return fail("快照文件不存在（可能已被清理）")
    content_bytes = full.read_bytes()

    # 复用统一恢复流程
    class _BytesFile:
        def __init__(self, name: str, data: bytes):
            self.filename = name
            self._data = data
        async def read(self): return self._data

    from fastapi.datastructures import UploadFile as _U
    upload = _U(filename=full.name, file=io.BytesIO(content_bytes))
    upload.file.read = lambda: content_bytes  # 兼容 sync 读
    return await _restore_from_bytes(db, filename=full.name, content=content_bytes)


async def _restore_from_bytes(db: Session, *, filename: str, content: bytes):
    raw_name = filename.lower()
    if not (raw_name.endswith(".ans") or raw_name.endswith(".zip")):
        return fail("备份格式不正确")
    if not content or len(content) > 200 * 1024 * 1024:
        return fail("备份为空或过大")
    try:
        zf = zipfile.ZipFile(io.BytesIO(content), "r")
    except zipfile.BadZipFile:
        return fail("备份文件已损坏或不是有效的 ZIP")
    names = set(zf.namelist())
    if MANIFEST_NAME not in names:
        return fail("备份缺少 manifest.json，无法识别格式")
    manifest = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
    sv = int(manifest.get("schema_version", 0))
    if sv > SCHEMA_VERSION:
        return fail(f"备份 schema={sv} 高于当前系统 {SCHEMA_VERSION}")
    data = {}
    try:
        for k, fn in TABLE_FILES.items():
            data[k] = json.loads(zf.read(fn).decode("utf-8")) if fn in names else []
    except Exception as e:
        return fail(f"备份 JSON 解析失败：{e}")
    for k in TABLE_FILES:
        if k not in data:
            return fail(f"备份不完整，缺少 {k}")
    current_ver = parse_version(get_app_version())
    snap_ver = parse_version(str(manifest.get("system_version", "0.0.0")))
    major_mismatch = snap_ver[0] != current_ver[0]

    def filter_rows(rows, model_cls):
        cols = {c.name for c in model_cls.__table__.columns}
        return [{k: v for k, v in row.items() if k in cols} for row in rows]

    filtered = {
        "categories": filter_rows(data["categories"], Category),
        "materials": filter_rows(data["materials"], Material),
        "projects": filter_rows(data["projects"], Project),
        "project_boms": filter_rows(data["project_boms"], ProjectBom),
        "stock_logs": filter_rows(data["stock_logs"], StockLog),
    }

    conn = db.connection().connection
    restored_imgs = 0
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM stock_log"); conn.execute("DELETE FROM project_bom")
        conn.execute("DELETE FROM project");   conn.execute("DELETE FROM material")
        conn.execute("DELETE FROM category")
        conn.execute("DELETE FROM conflict"); conn.execute("DELETE FROM operation_log")
        conn.execute("PRAGMA foreign_keys=ON")
        _bulk_insert(conn, "category", filtered["categories"], Category)
        _bulk_insert(conn, "material", filtered["materials"], Material)
        _bulk_insert(conn, "project", filtered["projects"], Project)
        _bulk_insert(conn, "project_bom", filtered["project_boms"], ProjectBom)
        _bulk_insert(conn, "stock_log", filtered["stock_logs"], StockLog)
        static_root = str(STATIC_DIR)
        os.makedirs(static_root, exist_ok=True)
        for img_name in _collect_image_names(filtered["materials"]):
            arc = STATIC_PREFIX + img_name
            if arc in names:
                img_bytes = zf.read(arc)
                dest = os.path.join(static_root, img_name)
                if os.path.commonpath([os.path.abspath(dest), os.path.abspath(static_root)]) != os.path.abspath(static_root):
                    continue
                with open(dest, "wb") as f: f.write(img_bytes)
                restored_imgs += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        try: conn.execute("PRAGMA foreign_keys=ON")
        except Exception: pass
        return fail(f"恢复失败，已全部回滚：{e}")
    db.expire_all()
    # 恢复属于批量数据集变更，阶段号 +1 并广播
    bump_global_check_code(db)
    db.commit()
    await ws_mgr.notify_restored(None, manifest.get("system_version", ""))
    return success({
        "stats": {
            "categories": len(filtered["categories"]),
            "materials": len(filtered["materials"]),
            "projects": len(filtered["projects"]),
            "project_boms": len(filtered["project_boms"]),
            "stock_logs": len(filtered["stock_logs"]),
            "images": restored_imgs,
        },
        "exported_at": manifest.get("exported_at", ""),
        "snapshot_system_version": manifest.get("system_version", ""),
        "current_version": get_app_version(),
        "major_mismatch": major_mismatch,
        "dropped_fields_note": "跨版本字段已自动过滤" if major_mismatch else "",
    }, "恢复成功" + ("（跨版本字段已自动过滤）" if major_mismatch else ""))


def _bulk_insert(conn, table_name: str, rows: List[Dict[str, Any]], model_cls: Any):
    if not rows:
        return
    columns = [c.name for c in model_cls.__table__.columns]
    cols_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    sql = f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({placeholders})'
    for row in rows:
        params = {c: row.get(c) for c in columns}
        conn.execute(sql, params)
