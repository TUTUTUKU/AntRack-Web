# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class CategoryIn(BaseModel):
    name: str = Field(..., max_length=100, description="分类名称")
    parent_id: int = Field(0, description="一级=0，二级绑定一级ID")
    level: int = Field(1, ge=1, le=2, description="1=一级，2=二级")
    sort: int = Field(0, ge=0, description="排序权重")


class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: int
    level: int
    sort: int

    class Config:
        from_attributes = True
