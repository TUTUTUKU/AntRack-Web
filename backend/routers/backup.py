# -*- coding: utf-8 -*-
"""
数据备份与恢复路由
- 仅导出：category / material / project / project_bom / stock_log + 引用到的 static 图片
- 不包含：user / license / device
- 备份格式：ZIP（扩展名 .antrack）
- 恢复：事务包裹，PRAGMA foreign_keys=OFF 删数据 → ON 后插入，失败全部回滚
"""
import io
import json
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import STATIC_DIR, STATIC_URL_PREFIX, BASE_DIR
from core.response import success, fail
from database import get_db
from dependencies import get_current_user
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


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """把 ORM 行对象按列名转成可 JSON 序列化的 dict"""
    out: Dict[str, Any] = {}
    for c in row.__table__.columns:
        v = getattr(row, c.name)
        # datetime → ISO 字符串，其它原样
        if isinstance(v, datetime):
            out[c.name] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            out[c.name] = v
    return out


def _strip_static_prefix(url: str) -> str:
    """把 /static/xxx.png 或 static/xxx.png 统一成 xxx.png（相对 static 目录的纯文件名）"""
    if not url:
        return ""
    p = url.strip()
    # 去掉前导斜杠
    if p.startswith("/"):
        p = p.lstrip("/")
    # 去掉 static/ 前缀
    if p.startswith(STATIC_PREFIX):
        p = p[len(STATIC_PREFIX):]
    return p


def _collect_image_names(materials: List[Dict[str, Any]]) -> List[str]:
    """收集所有物料引用到的图片文件名（去重）"""
    seen = []
    for m in materials:
        name = _strip_static_prefix(m.get("image") or "")
        if not name:
            continue
        if name not in seen:
            seen.append(name)
    return seen


@router.get("/export")
def export_backup(
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """一键下载备份：打包业务表 JSON + 引用到的物料图片
    仅含 category / material / project / project_bom / stock_log
    不含 user / license / device
    """
    if isinstance(user, User) is False:
        return fail("仅管理员可执行备份操作", code=403)

    categories = [_row_to_dict(r) for r in db.query(Category).all()]
    materials = [_row_to_dict(r) for r in db.query(Material).all()]
    projects = [_row_to_dict(r) for r in db.query(Project).all()]
    project_boms = [_row_to_dict(r) for r in db.query(ProjectBom).all()]
    stock_logs = [_row_to_dict(r) for r in db.query(StockLog).all()]

    manifest = {
        "schema_version": SCHEMA_VERSION,
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

    static_root = str(STATIC_DIR)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(TABLE_FILES["categories"], json.dumps(categories, ensure_ascii=False))
        zf.writestr(TABLE_FILES["materials"], json.dumps(materials, ensure_ascii=False))
        zf.writestr(TABLE_FILES["projects"], json.dumps(projects, ensure_ascii=False))
        zf.writestr(TABLE_FILES["project_boms"], json.dumps(project_boms, ensure_ascii=False))
        zf.writestr(TABLE_FILES["stock_logs"], json.dumps(stock_logs, ensure_ascii=False))

        # 只打包真正引用到的图片，避免 static 目录里的孤儿文件膨胀备份
        for img_name in _collect_image_names(materials):
            abs_path = os.path.join(static_root, img_name)
            if os.path.isfile(abs_path):
                zf.write(abs_path, arcname=STATIC_PREFIX + img_name)

    buf.seek(0)
    filename = f"antrack_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.antrack"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers=headers,
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: object = Depends(get_current_user),
):
    """上传 .antrack 备份文件并恢复业务数据
    - 严格事务：任意一步失败全部回滚，绝不出现半截状态
    - 恢复顺序：先 PRAGMA foreign_keys=OFF 删表（反依赖序），ON 后再 INSERT（正依赖序）
    - 仅覆盖业务表，user / license 完全不动
    """
    if isinstance(user, User) is False:
        return fail("仅管理员可执行恢复操作", code=403)

    # 1. 基础校验：扩展名 + 大小上限（200MB）
    raw_name = (file.filename or "").lower()
    if not raw_name.endswith(".antrack") and not raw_name.endswith(".zip"):
        return fail("备份文件格式不正确，请上传 .antrack 文件")
    content = await file.read()
    if not content:
        return fail("备份文件为空")
    if len(content) > 200 * 1024 * 1024:
        return fail("备份文件过大（>200MB），请检查是否选错文件")

    # 2. 解压并读取 manifest + 各业务表 JSON
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
        return fail("manifest.json 解析失败，文件已损坏")

    # schema 版本校验（不同 schema 不允许恢复，避免冲掉新字段）
    sv = int(manifest.get("schema_version", 0))
    if sv != SCHEMA_VERSION:
        return fail(
            f"备份 schema_version={sv} 与当前系统 {SCHEMA_VERSION} 不兼容，拒绝恢复"
        )

    # 读取各业务表 JSON
    try:
        data = {
            key: json.loads(zf.read(fname).decode("utf-8"))
            for key, fname in TABLE_FILES.items()
            if fname in names
        }
    except Exception as e:
        return fail(f"备份内 JSON 解析失败：{e}")

    # 必须五张表全齐，缺一不可
    for key in TABLE_FILES:
        if key not in data:
            return fail(f"备份不完整，缺少 {key}.json")

    # 3. 严格事务恢复：原样保留 ID，按依赖顺序删/插
    conn = db.connection().connection  # 拿到底层 DBAPI 连接，PRAGMA 必须走同一连接
    try:
        # 关闭外键约束，删除阶段不检查
        conn.execute("PRAGMA foreign_keys=OFF")
        # 先删（反依赖序）：流水 → BOM → 项目 → 物料 → 分类
        conn.execute("DELETE FROM stock_log")
        conn.execute("DELETE FROM project_bom")
        conn.execute("DELETE FROM project")
        conn.execute("DELETE FROM material")
        conn.execute("DELETE FROM category")
        # 重新开启外键约束后插入
        conn.execute("PRAGMA foreign_keys=ON")

        # 插入（正依赖序）：分类 → 物料 → 项目 → BOM → 流水
        _bulk_insert(conn, "category", data["categories"], Category)
        _bulk_insert(conn, "material", data["materials"], Material)
        _bulk_insert(conn, "project", data["projects"], Project)
        _bulk_insert(conn, "project_bom", data["project_boms"], ProjectBom)
        _bulk_insert(conn, "stock_log", data["stock_logs"], StockLog)

        # 4. 还原物料图片到 static 目录
        static_root = str(STATIC_DIR)
        os.makedirs(static_root, exist_ok=True)
        restored_imgs = 0
        for img_name in _collect_image_names(data["materials"]):
            arc = STATIC_PREFIX + img_name
            if arc in names:
                img_bytes = zf.read(arc)
                dest = os.path.join(static_root, img_name)
                # 防路径穿越：保证最终路径仍在 static_root 内
                if os.path.commonpath([os.path.abspath(dest), os.path.abspath(static_root)]) != os.path.abspath(static_root):
                    continue
                with open(dest, "wb") as f:
                    f.write(img_bytes)
                restored_imgs += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        # 兜底：恢复外键约束
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        return fail(f"恢复失败，已全部回滚：{e}")

    # 让当前 Session 失效缓存，避免后续读到旧对象
    db.expire_all()

    return success(
        {
            "stats": {
                "categories": len(data["categories"]),
                "materials": len(data["materials"]),
                "projects": len(data["projects"]),
                "project_boms": len(data["project_boms"]),
                "stock_logs": len(data["stock_logs"]),
                "images": restored_imgs,
            },
            "exported_at": manifest.get("exported_at", ""),
        },
        "恢复成功",
    )


def _bulk_insert(conn, table_name: str, rows: List[Dict[str, Any]], model_cls: Any):
    """按 ORM 模型的列顺序，对每行做参数化 INSERT，保留原始 ID
    - datetime 字段已在导出时转成 'YYYY-MM-DD HH:MM:SS' 字符串，SQLite 能直接存
    - 失败抛异常，由外层事务统一回滚
    """
    if not rows:
        return
    columns = [c.name for c in model_cls.__table__.columns]
    cols_sql = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    sql = f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({placeholders})'
    for row in rows:
        params = {c: row.get(c) for c in columns}
        conn.execute(sql, params)
