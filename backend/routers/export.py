# -*- coding: utf-8 -*-
import io
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import fail
from models.material import Material
from models.category import Category
from models.stock_log import StockLog
from models.project import Project
from models.project_bom import ProjectBom

router = APIRouter()


def _xlsx(df, filename: str) -> StreamingResponse:
    buf = io.BytesIO()
    with __import__("pandas").ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buf.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@router.get("/material")
def export_material(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    import pandas as pd
    items = db.query(Material).order_by(Material.id.asc()).all()
    rows = []
    for m in items:
        cat = db.query(Category).filter(Category.id == m.category_id).first()
        parent_name = ""
        if cat and cat.level == 2:
            p = db.query(Category).filter(Category.id == cat.parent_id).first()
            parent_name = p.name if p else ""
        rows.append({
            "ID": m.id,
            "物料名称": m.name,
            "一级分类": parent_name,
            "二级分类": cat.name if cat else "",
            "规格": m.spec,
            "实际库存": m.stock_total_num,
            "可用库存": round(m.stock_total_num - m.lock_num, 6),
            "锁定量": m.lock_num,
            "加权单价": m.stock_avg_price,
            "总成本": m.stock_total_cost,
            "告警阈值": m.warn_num,
            "备注": m.remark,
            "创建时间": m.create_time.strftime("%Y-%m-%d %H:%M:%S") if m.create_time else "",
        })
    df = pd.DataFrame(rows)
    return _xlsx(df, f"物料台账_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")


@router.get("/stock-log")
def export_stock_log(
    log_type: str = "",
    material_id: int = 0,
    project_id: int = 0,
    start_time: str = "",
    end_time: str = "",
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    import pandas as pd
    q = db.query(StockLog)
    if log_type:
        q = q.filter(StockLog.log_type == log_type)
    if material_id:
        q = q.filter(StockLog.material_id == material_id)
    if project_id:
        q = q.filter(StockLog.project_id == project_id)
    if start_time:
        q = q.filter(StockLog.create_time >= start_time)
    if end_time:
        q = q.filter(StockLog.create_time <= end_time + " 23:59:59")
    items = q.order_by(StockLog.id.desc()).all()
    type_map = {"in": "入库", "out_temp": "临时出库", "out_project": "项目出库", "lock": "锁定", "unlock": "解锁"}
    rows = []
    for l in items:
        m = db.query(Material).filter(Material.id == l.material_id).first()
        pname = ""
        if l.project_id:
            p = db.query(Project).filter(Project.id == l.project_id).first()
            pname = p.name if p else ""
        rows.append({
            "ID": l.id,
            "时间": l.create_time.strftime("%Y-%m-%d %H:%M:%S") if l.create_time else "",
            "物料名称": m.name if m else "(已删除)",
            "流水类型": type_map.get(l.log_type, l.log_type),
            "变动数量": l.num,
            "变动成本": l.cost,
            "操作后均价": l.avg_price,
            "关联项目": pname,
            "备注": l.remark,
        })
    df = pd.DataFrame(rows)
    return _xlsx(df, f"库存流水_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")


@router.get("/project/{project_id}")
def export_project(project_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    import pandas as pd
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return fail("项目不存在")
    boms = db.query(ProjectBom).filter(ProjectBom.project_id == project_id).order_by(ProjectBom.id.asc()).all()
    status_map = {"prepare": "准备阶段", "making": "制作阶段", "finish": "已归档"}
    rows = []
    for b in boms:
        m = db.query(Material).filter(Material.id == b.material_id).first()
        cat = db.query(Category).filter(Category.id == m.category_id).first() if m else None
        rows.append({
            "物料ID": b.material_id,
            "物料名称": m.name if m else "(已删除)",
            "分类": cat.name if cat else "",
            "规格": m.spec if m else "",
            "预估用量": b.plan_num,
            "锁定数量": b.lock_num,
            "已消耗数量": b.used_num,
            "物料加权单价": m.stock_avg_price if m else 0,
            "已消耗成本": round(b.used_num * (m.stock_avg_price if m else 0), 6),
        })
    df = pd.DataFrame(rows)
    # 在表头插入项目信息
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # 项目信息 sheet
        info_df = pd.DataFrame([
            {"项目名称": p.name, "状态": status_map.get(p.status, p.status),
             "简介": p.intro, "资料链接": p.link,
             "创建时间": p.create_time.strftime("%Y-%m-%d %H:%M:%S") if p.create_time else ""},
        ])
        info_df.to_excel(writer, index=False, sheet_name="项目信息")
        df.to_excel(writer, index=False, sheet_name="BOM清单")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="项目_{p.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'},
    )


@router.get("/project-list")
def export_project_list(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    import pandas as pd
    items = db.query(Project).order_by(Project.id.desc()).all()
    status_map = {"prepare": "准备阶段", "making": "制作阶段", "finish": "已归档"}
    rows = [{
        "ID": p.id, "项目名称": p.name, "状态": status_map.get(p.status, p.status),
        "简介": p.intro, "资料链接": p.link,
        "创建时间": p.create_time.strftime("%Y-%m-%d %H:%M:%S") if p.create_time else "",
    } for p in items]
    df = pd.DataFrame(rows)
    return _xlsx(df, f"项目列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
