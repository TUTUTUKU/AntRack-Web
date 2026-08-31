# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, File, UploadFile
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
    """删除项目：自动释放全部预占用，已消耗数据按已实际出库处理（不再回溯）"""
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    boms = db.query(ProjectBom).filter(ProjectBom.project_id == project_id).all()
    try:
        for b in boms:
            m = db.query(Material).filter(Material.id == b.material_id).first()
            release_lock = b.lock_num
            if m and release_lock > 0:
                m.lock_num = round(max(0.0, m.lock_num - release_lock), 6)
                log_unlock = StockLog(
                    material_id=m.id, project_id=p.id, log_type="unlock",
                    num=-release_lock, cost=0.0, avg_price=m.stock_avg_price,
                    remark=f"项目[{p.name}]删除，释放物料({release_lock})预占用",
                )
                db.add(log_unlock)
            db.delete(b)
        db.delete(p)
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"删除失败：{e}")
    return success(msg="项目删除成功，占用已归还")


@router.post("/bom/save")
def bom_save(data: BomIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """新增BOM明细：立即按预估用量预占用（lock_num = plan_num），可用库存不足时提示但仍允许保存（记录欠料）"""
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
        lock_num=data.plan_num,  # 新增即预占用
        used_num=0.0,
    )
    m.lock_num = round(m.lock_num + data.plan_num, 6)
    remark = f"项目[{p.name}]添加BOM自动锁定"
    try:
        db.add(bom)
        db.flush()
        log = StockLog(
            material_id=m.id, project_id=p.id, log_type="lock",
            num=data.plan_num, cost=0.0, avg_price=m.stock_avg_price, remark=remark,
        )
        db.add(log)
        db.commit()
        db.refresh(bom)
    except Exception as e:
        db.rollback()
        return fail(f"保存失败：{e}")
    usable = round(m.stock_total_num - m.lock_num, 6)
    shortage = max(0.0, -usable)
    msg = "BOM明细新增成功"
    if shortage > 0:
        msg += f"（欠料警告：可用库存不足，仍短缺 {shortage}）"
    return success({"id": bom.id}, msg)


@router.put("/bom/update-plan/{bom_id}")
def bom_update_plan(bom_id: int, data: BomUpdatePlanIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """修改预估用量：同步调整预占用数量（m.lock_num），已消耗部分不参与锁定调整"""
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if p and p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    if data.plan_num < bom.used_num:
        return fail(f"预估用量不能小于已消耗数量（{bom.used_num}）")
    m = db.query(Material).filter(Material.id == bom.material_id).first()
    old_lock = bom.lock_num
    new_lock = data.plan_num  # 预占用 = 预估用量 （已消耗部分不算在可用里，完工结算再扣）
    delta = round(new_lock - old_lock, 6)
    try:
        bom.plan_num = data.plan_num
        bom.lock_num = new_lock
        if m and delta != 0:
            m.lock_num = round(max(0.0, m.lock_num + delta), 6)
            if delta > 0:
                log = StockLog(
                    material_id=m.id, project_id=p.id if p else None, log_type="lock",
                    num=delta, cost=0.0, avg_price=m.stock_avg_price,
                    remark=f"项目[{p.name if p else ''}]修改预估用量增加锁定"
                )
            else:
                log = StockLog(
                    material_id=m.id, project_id=p.id if p else None, log_type="unlock",
                    num=delta, cost=0.0, avg_price=m.stock_avg_price,
                    remark=f"项目[{p.name if p else ''}]修改预估用量减少锁定"
                )
            db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"更新失败：{e}")
    return success(msg="预估用量已更新，预占用同步调整")


@router.delete("/bom/delete/{bom_id}")
def bom_delete(bom_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """删除BOM明细：自动释放未消耗的预占用数量（归还m.lock_num），已消耗部分按完工结算流程处理"""
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if p and p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    m = db.query(Material).filter(Material.id == bom.material_id).first()
    if bom.used_num > 0:
        return fail(f"该BOM已消耗{bom.used_num}，请先完工结算后再删除")
    # 释放预占用
    release_lock = bom.lock_num  # 未消耗，lock_num = plan_num
    try:
        if m and release_lock > 0:
            m.lock_num = round(max(0.0, m.lock_num - release_lock), 6)
            db.flush()
            log_unlock = StockLog(
                material_id=m.id, project_id=p.id if p else None, log_type="unlock",
                num=-release_lock, cost=0.0, avg_price=m.stock_avg_price,
                remark=f"项目[{p.name if p else ''}]删除BOM释放预占用",
            )
            db.add(log_unlock)
        db.delete(bom)
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"删除失败：{e}")
    return success(msg="BOM明细删除成功，占用已归还")


@router.post("/bom-consume/{bom_id}")
def bom_consume(bom_id: int, data: BomConsumeIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """BOM消耗：直接真实出库扣 actual stock（不需要等完工结算），同时从 bom.lock_num 释放对应预占用，写 StockLog out_project"""
    bom = db.query(ProjectBom).filter(ProjectBom.id == bom_id).first()
    if not bom:
        return fail("BOM明细不存在")
    p = db.query(Project).filter(Project.id == bom.project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，禁止消耗")
    if data.consume_num <= 0:
        return fail("消耗数量必须大于0")
    remain_lock = round(bom.lock_num - bom.used_num, 6)  # 可从预占用里扣除的量
    if data.consume_num > remain_lock:
        return fail(f"消耗数量超过可用预占用（当前剩余 {remain_lock}，已消耗 {bom.used_num}）")
    m = db.query(Material).filter(Material.id == bom.material_id).first()
    if not m:
        return fail("物料已被删除，无法消耗")
    if data.consume_num > m.stock_total_num:
        return fail(f"实际库存不足（当前 {m.stock_total_num}）")
    try:
        # 1) 真实出库：扣 m.stock_total_num / total_cost
        remain_num, remain_cost = calc_out_stock(
            old_num=m.stock_total_num,
            old_cost=m.stock_total_cost,
            out_num=data.consume_num,
            avg_price=m.stock_avg_price,
        )
        out_cost = round(data.consume_num * m.stock_avg_price, 6)
        m.stock_total_num = remain_num
        m.stock_total_cost = remain_cost
        # 2) 释放锁定：对应消耗的部分不再算锁定
        bom.lock_num = round(bom.lock_num - data.consume_num, 6)
        m.lock_num = round(max(0.0, m.lock_num - data.consume_num), 6)
        bom.used_num = round(bom.used_num + data.consume_num, 6)
        db.flush()
        log_out = StockLog(
            material_id=m.id, project_id=p.id, log_type="out_project",
            num=-data.consume_num, cost=out_cost, avg_price=m.stock_avg_price,
            remark=f"项目[{p.name}]BOM消耗出库",
        )
        db.add(log_out)
        log_unlock = StockLog(
            material_id=m.id, project_id=p.id, log_type="unlock",
            num=-data.consume_num, cost=0.0, avg_price=m.stock_avg_price,
            remark=f"项目[{p.name}]BOM消耗释放对应预占用",
        )
        db.add(log_unlock)
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"消耗失败：{e}")
    return success({
        "used_num": bom.used_num,
        "lock_num": bom.lock_num,
        "stock_total": m.stock_total_num,
        "stock_free": round(m.stock_total_num - m.lock_num, 6),
        "remain_can_consume": round(bom.lock_num - bom.used_num, 6),
    }, "消耗成功：真实库存已扣减")


@router.post("/finish-settle")
def finish_settle(project_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """完工结算：仅释放 BOM 剩余预占用（物料出库已在 bom-consume 时完成），避免重复扣减"""
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
            locked = bom.lock_num  # 剩存未消耗的预占用（= 预估用量 - 已消耗）
            used = bom.used_num
            # 已消耗部分 = 在 bom-consume 时已真实出库，这里不再二次扣
            out_cost = round(used * (m.stock_avg_price if m else 0), 6) if used > 0 else 0
            total_cost = round(total_cost + out_cost, 6)

            if m and locked > 0:
                # 释放未消耗的预占用
                m.lock_num = round(max(0.0, m.lock_num - locked), 6)
                db.flush()
                log_unlock = StockLog(
                    material_id=m.id, project_id=p.id, log_type="unlock",
                    num=-locked, cost=0.0, avg_price=m.stock_avg_price,
                    remark=f"项目[{p.name}]完工释放剩余预占用({locked})",
                )
                db.add(log_unlock)

            bom.lock_num = 0.0
            db.flush()
            settle_list.append({
                "material_id": bom.material_id,
                "material_name": m.name if m else "(已删除)",
                "used_num": used,
                "unlock_num": locked,
                "out_cost": out_cost,
                "skipped": m is None,
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


@router.post("/bom/import/{project_id}")
async def import_bom(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    """导入BOM表（Excel）：解析物料ID+预估用量，批量新增。已存在的物料跳过。"""
    import io
    import pandas as pd
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    if p.status == "finish":
        return fail("项目已归档，禁止修改BOM")
    # 读取上传文件
    raw = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(raw), sheet_name="BOM清单", engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        except Exception as e:
            return fail(f"Excel解析失败：{e}")
    if df is None or df.empty:
        return fail("Excel为空或无数据行")
    # 列名兼容（空格/大小写）
    df.columns = [str(c).strip() for c in df.columns]
    if "物料ID" not in df.columns or "预估用量" not in df.columns:
        return fail("Excel缺少必要列「物料ID」或「预估用量」，请使用导出的BOM模板填写")
    added, skipped_exist, skipped_invalid = 0, 0, 0
    for _, row in df.iterrows():
        mid = row.get("物料ID")
        plan = row.get("预估用量")
        # 跳过空行
        if mid is None or (isinstance(mid, float) and mid != mid) or plan is None:
            skipped_invalid += 1
            continue
        try:
            mid = int(float(mid))
            plan = float(plan)
        except Exception:
            skipped_invalid += 1
            continue
        if plan <= 0:
            skipped_invalid += 1
            continue
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            skipped_invalid += 1
            continue
        exists = db.query(ProjectBom).filter(
            ProjectBom.project_id == project_id,
            ProjectBom.material_id == mid,
        ).first()
        if exists:
            skipped_exist += 1
            continue
        # 导入即自动锁定
        bom = ProjectBom(
            project_id=project_id,
            material_id=mid,
            plan_num=plan,
            lock_num=plan,
            used_num=0.0,
        )
        m.lock_num = round(m.lock_num + plan, 6)
        db.add(bom)
        log = StockLog(
            material_id=m.id, project_id=project_id, log_type="lock",
            num=plan, cost=0.0, avg_price=m.stock_avg_price,
            remark=f"项目[{p.name}]导入BOM自动锁定",
        )
        db.add(log)
        added += 1
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return fail(f"导入失败：{e}")
    return success({
        "added": added,
        "skipped_exist": skipped_exist,
        "skipped_invalid": skipped_invalid,
    }, f"导入完成：新增 {added} 条，已存在跳过 {skipped_exist} 条，无效跳过 {skipped_invalid} 条")
