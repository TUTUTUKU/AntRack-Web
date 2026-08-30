# -*- coding: utf-8 -*-
"""冲突记录表：按物料维度合并"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from database import Base


class Conflict(Base):
    # 一条冲突 = 一个物料 + 同一阶段产生的多个冲突操作（合并展示）
    # snapshots_json 是数组，每个元素含 source/web/app、device、op_type、fixed_ts、
    # local_device_ts、time_correction_flag、diff_fields、summary 字段
    __tablename__ = "conflict"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, nullable=False, index=True)

    stage_code = Column(Integer, nullable=False)  # snapshot_global_check_code 触发时的阶段
    snapshots_json = Column(Text, default="[]", nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending / accepted / dismissed
    chosen_source_index = Column(Integer, nullable=True)  # 选择生效的 snapshots 下标
    related_log_ids = Column(String(255), default="", nullable=False)  # 逗号分隔的流水 id
    operator = Column(String(64), default="", nullable=False)  # 处理人
    create_time = Column(DateTime, default=datetime.now, nullable=False)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
