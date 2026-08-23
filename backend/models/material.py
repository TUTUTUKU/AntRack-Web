# -*- coding: utf-8 -*-
# models/material.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base


class Material(Base):
    __tablename__ = "material"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    category_id = Column(Integer, nullable=False)
    code = Column(String(64), default="", nullable=False)
    spec = Column(String(200), default="", nullable=False)
    unit = Column(String(20), default="个", nullable=False)
    price_unit = Column(String(10), default="¥", nullable=False)
    image = Column(String(255), default="", nullable=False)
    warn_num = Column(Float, default=0.0, nullable=False)
    remark = Column(String(500), default="", nullable=False)

    stock_total_num = Column(Float, default=0.0, nullable=False)
    stock_total_cost = Column(Float, default=0.0, nullable=False)
    stock_avg_price = Column(Float, default=0.0, nullable=False)
    lock_num = Column(Float, default=0.0, nullable=False)

    create_time = Column(DateTime, default=datetime.now, nullable=False)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
