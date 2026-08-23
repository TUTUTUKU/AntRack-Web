# -*- coding: utf-8 -*-
# models/stock_log.py
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
