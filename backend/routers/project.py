# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success, fail
from core.stock_calc import calc_out_stock
from models.project import Project
from models.project_bom import ProjectBom
from models.material import Material
from models.category import Category
from models.stock_log import StockLog
from schemas.project import ProjectIn, ProjectStatusIn
from schemas.project_bom import BomIn, BomUpdatePlanIn, BomConsumeIn, BomLockIn

router = APIRouter()


def _bom_to_dict(bom: ProjectBom, db: Session) -> dict:
    m = db.query(Material).filter(Material.id == bom.material_id).first()
    cat = db.query(Category).filter(Category.id == m.category_id).first() if m else None
    parent_name = ""
    if cat and cat.level == 2:
        p = db.query(Category).filter(Category.id == cat.parent_id).first()
        parent_name = p.name if p else ""
    return {
        "id": bom.id,
        "project_id": bom.project_id,
        "material_id": bom.material_id,
        "plan_num": bom.plan_num,
        "lock_num": bom.lock_num,
        "used_num": bom.used_num,
        "material_name": m.name if m else "(已删除)",
        "material_spec": m.spec if m else "",
        "material_image": m.image if m else "",
        "stock_total_num": m.stock_total_num if m else 0,
        "stock_avg_price": m.stock_avg_price if m else 0,
        "usable_stock": round(m.stock_total_num - m.lock_num, 6) if m else 0,
        "category_name": cat.name if cat else "",
        "parent_category_name": parent_name,
    }


def _project_to_dict(p: Project, db: Session) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "intro": p.intro,
        "link": p.link,
        "create_time": p.create_time.strftime("%Y-%m-%d %H:%M:%S") if p.create_time else "",
        "update_time": p.update_time.strftime("%Y-%m-%d %H:%M:%S") if p.update_time else "",
    }


@router.get("/list")
def list_project(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(Project)
    if keyword:
        q = q.filter(Project.name.like(f"%{keyword}%"))
    if status in ("prepare", "making", "finish"):
        q = q.filter(Project.status == status)
    total = q.count()
    items = q.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return success({
        "total": total, "page": page, "page_size": page_size,
        "list": [_project_to_dict(p, db) for p in items],
    })


@router.get("/detail/{project_id}")
def detail(project_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    boms = db.query(ProjectBom).filter(ProjectBom.project_id == project_id).order_by(ProjectBom.id.asc()).all()
    return success({
        "project": _project_to_dict(p, db),
        "bom_list": [_bom_to_dict(b, db) for b in boms],
    })


@router.post("/save")
def save(data: ProjectIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = Project(name=data.name.strip(), intro=data.intro, link=data.link, status="prepare")
    db.add(p)
    db.commit()
    db.refresh(p)
    return success({"id": p.id}, "项目创建成功")


@router.put("/update/{project_id}")
def update(project_id: int, data: ProjectIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    p.name = data.name.strip()
    p.intro = data.intro
    p.link = data.link
    db.commit()
    return success(msg="项目修改成功")


@router.put("/status/{project_id}")
def switch_status(project_id: int, data: ProjectStatusIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，不可修改状态")
    if data.status == "finish":
        return fail("完工归档请使用完工结算接口")
    p.status = data.status
    db.commit()
    return success(msg="状态切换成功")


@router.delete("/delete/{project_id}")
def delete(project_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    boms = db.query(ProjectBom).filter(ProjectBom.project_id == project_id).all()
    if p.status != "finish":
        for b in boms:
            if b.lock_num > 0:
                return fail("项目存在锁定物料，请先解锁后再删除")
            if b.used_num > 0:
                return fail("项目存在已消耗未结算物料，请先完工结算后再删除")
    for b in boms:
        db.delete(b)
    db.delete(p)
    db.commit()
    return success(msg="项目删除成功")


@router.post("/bom/save")
def bom_save(data: BomIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == data.project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    m = db.query(Material).filter(Material.id == data.material_id).first()
    if not m:
        return fail("物料不存在")
    exists = db.query(ProjectBom).filter(
        ProjectBom.project_id == data.project_id,
        ProjectBom.material_id == data.material_id,
    ).first()
    if exists:
        return fail("该物料已在BOM中，请勿重复添加")
    bom = ProjectBom(
        project_id=data.project_id,
        material_id=data.material_id,
        plan_num=data.plan_num,
        lock_num=0.0,
        used_num=0.0,
    )
    db.add(bom)
    db.commit()
    db.refresh(bom)
    return success({"id": bom.id}, "BOM明细新增成功")


@router.put("/bom/update-plan/{bom_id}")
def bom_update_plan(bom_id: int, data: BomUpdatePlanIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if p and p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    bom.plan_num = data.plan_num
    db.commit()
    return success(msg="预估用量已更新")


@router.delete("/bom/delete/{bom_id}")
def bom_delete(bom_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if p and p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    if bom.lock_num > 0:
        return fail("该BOM明细存在锁定数量，请先解锁后再删除")
    if bom.used_num > 0:
        return fail("该BOM明细存在已消耗数量，请先完工结算后再删除")
    db.delete(bom)
    db.commit()
    return success(msg="BOM明细删除成功")


@router.post("/bom-lock")
def bom_lock(data: BomLockIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == data.project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，禁止锁定/解锁")
    m = db.query(Material).filter(Material.id == data.material_id).first()
    if not m:
        return fail("物料不存在")
    bom = db.query(ProjectBom).filter(
        ProjectBom.project_id == data.project_id,
        ProjectBom.material_id == data.material_id,
    ).first()
    if not bom:
        return fail("BOM明细不存在，请先添加")

    if data.lock_num == 0:
        return fail("锁定数量不能为0")

    try:
        if data.lock_num > 0:
            usable = m.stock_total_num - m.lock_num
            if data.lock_num > usable:
                return fail(f"可用库存不足（当前可用 {int(round(usable))}），无法锁定")
            bom.lock_num = round(bom.lock_num + data.lock_num, 6)
            m.lock_num = round(m.lock_num + data.lock_num, 6)
            log_type = "lock"
            log_num = data.lock_num
        else:
            unlock_num = -data.lock_num
            if unlock_num > bom.lock_num:
                return fail(f"解锁数量超出当前BOM锁定量（{int(round(bom.lock_num))}）")
            bom.lock_num = round(bom.lock_num - unlock_num, 6)
            m.lock_num = round(m.lock_num - unlock_num, 6)
            log_type = "unlock"
            log_num = -unlock_num
        db.flush()
        log = StockLog(
            material_id=m.id,
            project_id=p.id,
            log_type=log_type,
            num=log_num,
            cost=0.0,
            avg_price=m.stock_avg_price,
            remark=data.remark,
        )
        db.add(log)
        db.commit()
        return success({
            "material_lock_total": m.lock_num,
            "bom_lock_num": bom.lock_num,
            "usable_stock": round(m.stock_total_num - m.lock_num, 6),
        }, "锁定/解锁成功")
    except Exception as e:
        db.rollback()
        return fail(f"操作失败：{str(e)}")


@router.post("/bom-consume/{bom_id}")
def bom_consume(bom_id: int, data: BomConsumeIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status != "making":
        return fail("仅制作阶段可确认消耗")
    if data.consume_num <= 0:
        return fail("消耗数量必须大于0")
    if bom.used_num + data.consume_num > bom.lock_num:
        return fail(f"消耗数量超出锁定数量（当前锁定 {int(round(bom.lock_num))}，已消耗 {int(round(bom.used_num))}）")
    bom.used_num = round(bom.used_num + data.consume_num, 6)
    db.commit()
    return success({
        "used_num": bom.used_num,
        "lock_num": bom.lock_num,
        "remain_can_consume": round(bom.lock_num - bom.used_num, 6),
    }, "消耗确认成功")


@router.post("/finish-settle")
def finish_settle(project_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，不可重复结算")

    boms = db.query(ProjectBom).filter(ProjectBom.project_id == project_id).all()
    settle_list = []
    total_cost = 0.0

    try:
        for bom in boms:
            m = db.query(Material).filter(Material.id == bom.material_id).first()
            if not m:
                settle_list.append({
                    "material_id": bom.material_id,
                    "material_name": "(已删除)",
                    "used_num": bom.used_num,
                    "lock_num": bom.lock_num,
                    "unlock_num": 0,
                    "out_cost": 0,
                    "skipped": True,
                })
                continue

            used = bom.used_num
            locked = bom.lock_num
            unlock_part = locked - used

            if used > 0:
                remain_num, remain_cost = calc_out_stock(
                    old_num=m.stock_total_num,
                    old_cost=m.stock_total_cost,
                    out_num=used,
                    avg_price=m.stock_avg_price,
                )
                out_cost = round(used * m.stock_avg_price, 6)
                m.stock_total_num = remain_num
                m.stock_total_cost = remain_cost
                db.flush()
                log_out = StockLog(
                    material_id=m.id,
                    project_id=p.id,
                    log_type="out_project",
                    num=-used,
                    cost=out_cost,
                    avg_price=m.stock_avg_price,
                    remark=f"项目[{p.name}]完工自动出库",
                )
                db.add(log_out)
                total_cost = round(total_cost + out_cost, 6)

            if locked > 0:
                m.lock_num = round(m.lock_num - locked, 6)
                if m.lock_num < 0:
                    m.lock_num = 0.0
                if unlock_part > 0:
                    log_unlock = StockLog(
                        material_id=m.id,
                        project_id=p.id,
                        log_type="unlock",
                        num=-unlock_part,
                        cost=0.0,
                        avg_price=m.stock_avg_price,
                        remark=f"项目[{p.name}]完工释放剩余锁定",
                    )
                    db.add(log_unlock)
                bom.lock_num = 0.0
            db.flush()

            settle_list.append({
                "material_id": m.id,
                "material_name": m.name,
                "used_num": used,
                "lock_num": locked,
                "unlock_num": round(unlock_part, 6) if unlock_part > 0 else 0,
                "out_cost": round(used * m.stock_avg_price, 6) if used > 0 else 0,
                "skipped": False,
            })

        p.status = "finish"
        db.commit()
        return success({
            "settle_list": settle_list,
            "total_cost": total_cost,
            "finish_project_status": "finish",
        }, "项目完工结算成功")
    except Exception as e:
        db.rollback()
        return fail(f"完工结算失败，已回滚：{str(e)}")
