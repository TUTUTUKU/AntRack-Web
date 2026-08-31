# -*- coding: utf-8 -*-
"""操作日志表：服务端日志，保留 1 年；APP 同步后写入；Web 业务写入"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base


class OperationLog(Base):
    __tablename__ = "operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), default="", nullable=False, index=True)   # user 或 device 绑定人
    source = Column(String(16), default="web", nullable=False)              # web / app
    device_id = Column(String(128), default="", nullable=False)             # app 端有，web 留空
    action = Column(String(64), nullable=False, index=True)                 # material_update / stock_in / stock_out / project_create / backup_restore / undo ...
    material_id = Column(Integer, nullable=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)
    related_log_id = Column(Integer, nullable=True)                         # 关联库存流水 id（如有）
    detail_json = Column(Text, default="{}", nullable=False)                # 详细 JSON
    ip = Column(String(64), default="", nullable=False)
    effective_time = Column(DateTime, default=datetime.now, nullable=False, index=True)  # 业务生效时间，用于撤销
    create_time = Column(DateTime, default=datetime.now, nullable=False)
    revoke_status = Column(String(16), default="ok", nullable=False)        # ok / revoked / invalid
