# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Any


class OperationLogOut(BaseModel):
    id: int
    username: str
    source: str
    device_id: str = ""
    action: str
    material_id: int | None = None
    project_id: int | None = None
    related_log_id: int | None = None
    detail: dict = Field(default_factory=dict)
    ip: str = ""
    effective_time: str = ""
    revoke_status: str = "ok"
    can_undo: bool = False  # 是否在 5 分钟撤销窗口内

    class Config:
        from_attributes = True


class OperationLogQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    material_id: int | None = None
    project_id: int | None = None
    start_time: str = ""
    end_time: str = ""
    action: str = ""
    source: str = ""
