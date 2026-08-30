# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Any, Optional


class ConflictSnapshot(BaseModel):
    source: str = Field(..., description="web / app")
    device: str = Field("", description="用户名/设备ID")
    op_type: str = Field(..., description="material_update / stock_in / stock_out_temp / stock_out_project / lock / unlock / bom_change / project_create / project_status ...")
    fixed_ts: str = Field("", description="校正后业务时间字符串")
    local_device_ts: str = Field("", description="设备原始本地时间（仅供参考）")
    time_correction_flag: str = Field("", description="ok / forced / 空")
    diff_fields: dict = Field(default_factory=dict)
    summary: str = Field("")


class ConflictResolveIn(BaseModel):
    status: str = Field(..., description="accepted / dismissed")
    chosen_snapshot_index: Optional[int] = Field(None, description="accepted 时需要的生效版本快照下标")


class ConflictBatchResolveIn(BaseModel):
    ids: list[int]
    status: str = Field(..., description="accepted / dismissed")
    chosen_indexes: dict = Field(default_factory=dict, description="{冲突id: snapshot下标}")


class ConflictOut(BaseModel):
    id: int
    material_id: int
    stage_code: int
    snapshots: list[ConflictSnapshot] = []
    status: str
    chosen_source_index: Optional[int] = None
    related_log_ids: str = ""
    operator: str = ""
    create_time: str = ""
    update_time: str = ""

    class Config:
        from_attributes = True
