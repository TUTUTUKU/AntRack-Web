# -*- coding: utf-8 -*-
# models/category.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    sort = Column(Integer, default=0, nullable=False)
    create_time = Column(DateTime, default=datetime.now, nullable=False)
