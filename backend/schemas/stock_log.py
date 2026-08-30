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
    server_commit_ts: str = ""
    local_device_ts: str = ""
    time_correction_flag: str = ""
    source: str = "web"
    device_id: str = ""
    invalid: int = 0
    revoke_status: str = "ok"
    can_undo: bool = False

    class Config:
        from_attributes = True
