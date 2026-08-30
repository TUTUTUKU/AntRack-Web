# -*- coding: utf-8 -*-
# APP 同步握手 + 离线队列批量上传 schema
from pydantic import BaseModel, Field
from typing import Any, Optional


class HandshakeOut(BaseModel):
    current_global_check_code: int
    current_server_time: str  # YYYY-MM-DD HH:MM:SS
    version: str  # X.Y.Z
    stage_changed_since_last: bool  # 与上一次 global_check_code 相比是否有阶段变更
    latest_backup_meta: dict = Field(default_factory=dict)  # {id, create_time, version, file_size}，无备份时为 {}
    pending_conflict_count: int = 0  # 当前用户未处理的冲突总数


class OfflineOp(BaseModel):
    # APP 离线待同步操作单条
    idempotency_key: str = Field(..., max_length=64, description="APP 生成唯一幂等键，服务端防重复")
    op_type: str = Field(..., description="stock_in / stock_out_temp / material_update / material_create / bom_lock / bom_unlock / project_create")
    local_device_ts: str = Field("", description="YYYY-MM-DD HH:MM:SS 或 ISO 格式")
    payload: dict = Field(default_factory=dict)


class OfflineSyncIn(BaseModel):
    # APP 联网提交的离线操作包
    snapshot_global_check_code: int  # 离线断开瞬间服务端 global_check_code
    snapshot_server_time: str  # 离线断开瞬间服务端时间 YYYY-MM-DD HH:MM:SS
    ops: list[OfflineOp] = Field(default_factory=list)


class OpResult(BaseModel):
    idempotency_key: str
    ok: bool
    error: str = ""
    log_id: int | None = None
    time_correction_flag: str = ""
    fixed_ts: str = ""
    triggered_conflict_id: int | None = None
