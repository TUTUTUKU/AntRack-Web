# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    name: str = Field(..., max_length=120, description="项目名称")
    intro: str = Field("", max_length=500, description="项目简介")
    link: str = Field("", max_length=255, description="资料链接")


class ProjectOut(BaseModel):
    id: int
    name: str
    status: str
    intro: str
    link: str

    class Config:
        from_attributes = True


class ProjectStatusIn(BaseModel):
    status: str = Field(..., pattern="^(prepare|making|finish)$")
