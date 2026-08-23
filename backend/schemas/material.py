# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class MaterialIn(BaseModel):
    name: str = Field(..., max_length=120, description="物料名称")
    category_id: int = Field(..., description="绑定二级分类ID")
    code: str = Field("", max_length=64, description="物料编码")
    spec: str = Field("", max_length=200, description="规格参数")
    unit: str = Field("个", max_length=20, description="计数单位")
    price_unit: str = Field("¥", max_length=10, description="价格单位")
    image: str = Field("", max_length=255, description="图片路径")
    warn_num: float = Field(0.0, ge=0, description="最低告警库存")
    remark: str = Field("", max_length=500, description="备注")
    init_stock: float = Field(0.0, ge=0, description="初始库存数量（仅新增时有效）")
    init_cost: float = Field(0.0, ge=0, description="初始入库单价（仅新增时有效）")


class MaterialOut(BaseModel):
    id: int
    name: str
    category_id: int
    code: str = ""
    spec: str
    unit: str = "个"
    price_unit: str = "¥"
    image: str
    warn_num: float
    remark: str
    stock_total_num: float
    stock_total_cost: float
    stock_avg_price: float
    lock_num: float
    usable_stock: float = 0.0
    category_name: str = ""
    parent_category_name: str = ""

    class Config:
        from_attributes = True


class StockInIn(BaseModel):
    material_id: int
    in_num: float = Field(..., gt=0, description="入库数量，必须大于0")
    pay_total: float = Field(..., ge=0, description="本次实付总价，必须≥0")
    remark: str = Field("", description="备注")


class StockInOut(BaseModel):
    new_stock_num: float
    new_stock_cost: float
    new_avg_price: float
    log_id: int


class StockOutTempIn(BaseModel):
    material_id: int
    out_num: float = Field(..., gt=0, description="出库数量，大于0且≤实际库存")
    remark: str = Field("", description="备注")


class StockOutTempOut(BaseModel):
    remain_num: float
    remain_cost: float
    avg_price: float
    log_id: int
