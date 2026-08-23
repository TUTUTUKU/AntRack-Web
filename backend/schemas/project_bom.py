# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class BomIn(BaseModel):
    project_id: int
    material_id: int
    plan_num: float = Field(0.0, ge=0, description="预估用量")


class BomUpdatePlanIn(BaseModel):
    plan_num: float = Field(..., ge=0, description="预估用量")


class BomConsumeIn(BaseModel):
    consume_num: float = Field(..., gt=0, description="本次确认消耗数量")
    remark: str = Field("", description="备注")


class BomLockIn(BaseModel):
    project_id: int
    material_id: int
    lock_num: float = Field(..., description="正数锁定、负数解锁")
    remark: str = Field("", description="备注")


class BomLockOut(BaseModel):
    material_lock_total: float
    bom_lock_num: float
    usable_stock: float


class FinishSettleOut(BaseModel):
    settle_list: list
    total_cost: float
    finish_project_status: str = "finish"
