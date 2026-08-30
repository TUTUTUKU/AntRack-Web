# -*- coding: utf-8 -*-
"""操作日志 Service：Web / App 统一写入"""
from __future__ import annotations

import json
from datetime import datetime
from sqlalchemy.orm import Session

from models.operation_log import OperationLog


def write_op_log(
    db: Session,
    *,
    username: str,
    source: str,
    action: str,
    material_id: int | None = None,
    project_id: int | None = None,
    related_log_id: int | None = None,
    detail: dict | None = None,
    ip: str = "",
    device_id: str = "",
    effective_time: datetime | None = None,
) -> OperationLog:
    log = OperationLog(
        username=username or "",
        source=source,
        device_id=device_id or "",
        action=action,
        material_id=material_id,
        project_id=project_id,
        related_log_id=related_log_id,
        detail_json=json.dumps(detail or {}, ensure_ascii=False),
        ip=ip or "",
        effective_time=effective_time or datetime.now(),
    )
    db.add(log)
    db.flush()
    return log
