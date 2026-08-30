# -*- coding: utf-8 -*-
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from config import STATIC_DIR, STATIC_URL_PREFIX
from core.response import success, fail
from core.stock_calc import calc_new_avg_price, calc_out_stock
from models.material import Material
from models.category import Category
from models.stock_log import StockLog
from models.project_bom import ProjectBom
from schemas.material import MaterialIn, StockInIn, StockOutTempIn

router = APIRouter()


def _enrich(m: Material, db: Session) -> dict:
    cat = db.query(Category).filter(Category.id == m.category_id).first()
    category_name = cat.name if cat else ""
    parent_category_name = ""
    if cat and cat.level == 2:
        parent = db.query(Category).filter(Category.id == cat.parent_id).first()
        parent_category_name = parent.name if parent else ""
    return {
        "id": m.id,
        "name": m.name,
        "category_id": m.category_id,
        "code": m.code,
        "spec": m.spec,
        "unit": m.unit,
        "price_unit": m.price_unit,
        "image": m.image,
        "warn_num": m.warn_num,
        "remark": m.remark,
        "stock_total_num": m.stock_total_num,
        "stock_total_cost": m.stock_total_cost,
        "stock_avg_price": m.stock_avg_price,
        "lock_num": m.lock_num,
        "usable_stock": round(m.stock_total_num - m.lock_num, 6),
        "category_name": category_name,
        "parent_category_name": parent_category_name,
        "create_time": m.create_time.strftime("%Y-%m-%d %H:%M:%S") if m.create_time else "",
        "update_time": m.update_time.strftime("%Y-%m-%d %H:%M:%S") if m.update_time else "",
        "server_commit_ts": (m.server_commit_ts.strftime("%Y-%m-%d %H:%M:%S")
                             if getattr(m, "server_commit_ts", None) else "") or "",
    }


@router.get("/list")
def list_material(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    category_id: Optional[int] = None,
    parent_category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(Material)
    if keyword:
        q = q.filter(Material.name.like(f"%{keyword}%"))
    if category_id:
        q = q.filter(Material.category_id == category_id)
    elif parent_category_id:
        sub_ids = [c.id for c in db.query(Category).filter(Category.parent_id == parent_category_id, Category.level == 2).all()]
        if sub_ids:
            q = q.filter(Material.category_id.in_(sub_ids))
        else:
            q = q.filter(Material.id == -1)

    total = q.count()
    items = q.order_by(Material.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [_enrich(m, db) for m in items],
    })


@router.get("/all")
def all_material(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    items = db.query(Material).order_by(Material.id.desc()).all()
    return success([_enrich(m, db) for m in items])


@router.get("/detail/{material_id}")
def detail(material_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        return fail("物料不存在")
    return success(_enrich(m, db))


def _generate_next_code(db: Session) -> str:
    """按 AR+6 位数字格式生成下一个物料编码"""
    max_code_row = (
        db.query(Material.code)
        .filter(Material.code.like("AR%"))
        .order_by(Material.code.desc())
        .first()
    )
    max_n = 0
    if max_code_row and max_code_row[0] and len(max_code_row[0]) == 8:
        try:
            max_n = int(max_code_row[0][2:])
        except ValueError:
            max_n = 0
    return f"AR{max_n + 1:06d}"


@router.get("/next-code")
def next_code(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    return success({"code": _generate_next_code(db)})


@router.post("/save")
def save(data: MaterialIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    cat = db.query(Category).filter(Category.id == data.category_id, Category.level == 2).first()
    if not cat:
        return fail("物料必须绑定有效的二级分类")

    # 未传编码时自动生成
    code = (data.code or "").strip()
    if not code:
        code = _generate_next_code(db)

    # 初始库存：init_stock > 0 时写一条入库流水（init_cost 为初始入库单价）
    init_num = data.init_stock or 0.0
    init_price = data.init_cost or 0.0
    init_cost_total = round(init_num * init_price, 6)
    init_avg_price = init_price if init_num > 0 else 0.0

    m = Material(
        name=data.name.strip(),
        category_id=data.category_id,
        code=code,
        spec=data.spec,
        unit=data.unit.strip() or "个",
        price_unit=data.price_unit.strip() or "¥",
        image=data.image,
        warn_num=data.warn_num,
        remark=data.remark,
        stock_total_num=init_num,
        stock_total_cost=init_cost_total,
        stock_avg_price=init_avg_price,
    )
    db.add(m)
    db.flush()

    # 库存仅由流水驱动，初始库存 > 0 必须写一条入库流水
    if init_num > 0:
        log = StockLog(
            material_id=m.id,
            project_id=None,
            log_type="in",
            num=init_num,
            cost=init_cost_total,
            avg_price=init_avg_price,
            remark="初始入库",
        )
        db.add(log)

    db.commit()
    db.refresh(m)
    return success({"id": m.id, "code": m.code}, "物料新增成功")


@router.put("/update/{material_id}")
def update(material_id: int, data: MaterialIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        return fail("物料不存在")
    cat = db.query(Category).filter(Category.id == data.category_id, Category.level == 2).first()
    if not cat:
        return fail("物料必须绑定有效的二级分类")
    m.name = data.name.strip()
    m.category_id = data.category_id
    m.code = data.code.strip()
    m.spec = data.spec
    m.unit = data.unit.strip() or "个"
    m.price_unit = data.price_unit.strip() or "¥"
    m.image = data.image
    m.warn_num = data.warn_num
    m.remark = data.remark
    db.commit()
    return success(msg="物料修改成功")


@router.delete("/delete/{material_id}")
def delete(material_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        return fail("物料不存在")
    if m.lock_num > 0:
        return fail(f"物料存在项目锁定量 {int(round(m.lock_num))}，请先解锁后再删除")
    bom_count = db.query(ProjectBom).filter(ProjectBom.material_id == material_id).count()
    if bom_count > 0:
        return fail(f"物料被 {bom_count} 个项目BOM引用，请先移除BOM引用后再删除")
    db.delete(m)
    db.commit()
    return success(msg="物料删除成功")


class _BatchDeleteIn(BaseModel):
    ids: list[int]


@router.post("/delete-batch")
def delete_batch(data: _BatchDeleteIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    ids = list({int(x) for x in data.ids})
    if not ids:
        return fail("未选择任何物料")
    items = db.query(Material).filter(Material.id.in_(ids)).all()
    if len(items) != len(ids):
        return fail("部分物料不存在，请刷新后重试")
    for m in items:
        if m.lock_num > 0:
            return fail(f"物料「{m.name}」存在项目锁定量 {int(round(m.lock_num))}，请先解锁后再删除")
        bom_count = db.query(ProjectBom).filter(ProjectBom.material_id == m.id).count()
        if bom_count > 0:
            return fail(f"物料「{m.name}」被 {bom_count} 个项目BOM引用，请先移除后再删除")
    for m in items:
        db.delete(m)
    db.commit()
    return success({"deleted": len(items)}, f"批量删除成功，共 {len(items)} 条")


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), _: object = Depends(get_current_user)):
    if not file.filename:
        return fail("未选择文件")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        return fail("仅支持 png/jpg/jpeg/gif/webp/bmp 格式")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return fail("图片大小不能超过 5MB")
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = STATIC_DIR / filename
    save_path.write_bytes(content)
    return success({"url": f"{STATIC_URL_PREFIX}/{filename}", "path": f"{STATIC_URL_PREFIX}/{filename}"}, "上传成功")


@router.post("/stock-in")
def stock_in(data: StockInIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == data.material_id).first()
    if not m:
        return fail("物料不存在")
    if data.in_num <= 0:
        return fail("入库数量必须大于0")
    if data.pay_total < 0:
        return fail("实付总价不能为负数")

    try:
        new_num, new_cost, new_avg = calc_new_avg_price(
            old_num=m.stock_total_num,
            old_cost=m.stock_total_cost,
            add_num=data.in_num,
            add_cost=data.pay_total,
        )
        m.stock_total_num = new_num
        m.stock_total_cost = new_cost
        m.stock_avg_price = new_avg
        db.flush()
        log = StockLog(
            material_id=m.id,
            project_id=None,
            log_type="in",
            num=data.in_num,
            cost=data.pay_total,
            avg_price=new_avg,
            remark=data.remark,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return success({
            "new_stock_num": new_num,
            "new_stock_cost": new_cost,
            "new_avg_price": new_avg,
            "log_id": log.id,
        }, "入库成功")
    except Exception as e:
        db.rollback()
        return fail(f"入库失败：{str(e)}")


@router.post("/stock-out-temp")
def stock_out_temp(data: StockOutTempIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    m = db.query(Material).filter(Material.id == data.material_id).first()
    if not m:
        return fail("物料不存在")
    if data.out_num <= 0:
        return fail("出库数量必须大于0")
    if data.out_num > m.stock_total_num:
        return fail(f"出库数量超出实际库存（当前库存 {int(round(m.stock_total_num))}）")

    try:
        remain_num, remain_cost = calc_out_stock(
            old_num=m.stock_total_num,
            old_cost=m.stock_total_cost,
            out_num=data.out_num,
            avg_price=m.stock_avg_price,
        )
        m.stock_total_num = remain_num
        m.stock_total_cost = remain_cost
        db.flush()
        log = StockLog(
            material_id=m.id,
            project_id=None,
            log_type="out_temp",
            num=-data.out_num,
            cost=round(data.out_num * m.stock_avg_price, 6),
            avg_price=m.stock_avg_price,
            remark=data.remark,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return success({
            "remain_num": remain_num,
            "remain_cost": remain_cost,
            "avg_price": m.stock_avg_price,
            "log_id": log.id,
        }, "临时出库成功")
    except Exception as e:
        db.rollback()
        return fail(f"出库失败：{str(e)}")
