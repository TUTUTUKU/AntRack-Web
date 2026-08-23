# -*- coding: utf-8 -*-
from pydantic import BaseModel


class StockLogOut(BaseModel):
    id: int
    material_id: int
    project_id: int | None = None
    log_type: str
    num: float
    cost: float
    avg_price: float
    remark: str
    material_name: str = ""
    project_name: str = ""

    class Config:
        from_attributes = True
