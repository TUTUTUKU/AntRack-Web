# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base


class StockLog(Base):
    __tablename__ = "stock_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=True, default=None)
    log_type = Column(String(20), nullable=False)  # in/out_temp/out_project/lock/unlock
    num = Column(Float, nullable=False, default=0.0)
    cost = Column(Float, nullable=False, default=0.0)
    avg_price = Column(Float, nullable=False, default=0.0)
    remark = Column(String(500), default="", nullable=False)

    create_time = Column(DateTime, default=datetime.now, nullable=False)
    server_commit_ts = Column(DateTime, default=datetime.now, nullable=False)  # 业务真实时间（服务端或 APP 时间偏移校正后），界面优先展示
    local_device_ts = Column(DateTime, nullable=True)  # 设备原始本地时间，断电/断网/时间错乱时可能不准，仅作参考元数据
    time_correction_flag = Column(String(20), default="", nullable=False)  # 空=未校正; ok=校正后落在区间内; forced=超出区间强制用当前服务时间
    source = Column(String(16), default="web", nullable=False)  # web / app
    device_id = Column(String(128), default="", nullable=False)  # APP 端设备标识，Web 留空
    client_op_idempotency_key = Column(String(64), default="", nullable=False)  # APP 离线操作幂等键，防止重复同步提交
    invalid = Column(Integer, default=0, nullable=False)  # 0=有效；1=已被撤销/回滚失效（对外返回过滤）
    revoke_status = Column(String(16), default="ok", nullable=False)  # ok / revoking / revoked

