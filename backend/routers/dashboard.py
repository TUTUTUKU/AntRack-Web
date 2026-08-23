# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success
from models.material import Material
from models.project import Project
from models.stock_log import StockLog

router = APIRouter()


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    material_count = db.query(Material).count()
    project_count = db.query(Project).count()
    making_count = db.query(Project).filter(Project.status == "making").count()
    total_cost = sum(m.stock_total_cost for m in db.query(Material).all())

    warn_list = []
    for m in db.query(Material).all():
        if m.warn_num > 0 and m.stock_total_num <= m.warn_num:
            warn_list.append({
                "id": m.id, "name": m.name,
                "stock_total_num": m.stock_total_num,
                "warn_num": m.warn_num,
                "usable_stock": round(m.stock_total_num - m.lock_num, 6),
            })

    prepare_count = db.query(Project).filter(Project.status == "prepare").count()
    making_c = making_count
    finish_count = db.query(Project).filter(Project.status == "finish").count()

    return success({
        "material_count": material_count,
        "project_count": project_count,
        "making_count": making_c,
        "total_cost": round(total_cost, 6),
        "warn_list": warn_list,
        "project_status": {
            "prepare": prepare_count,
            "making": making_c,
            "finish": finish_count,
        },
    })
