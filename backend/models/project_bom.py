# -*- coding: utf-8 -*-
# models/project_bom.py
from sqlalchemy import Column, Integer, Float
from database import Base


class ProjectBom(Base):
    __tablename__ = "project_bom"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    material_id = Column(Integer, nullable=False)
    plan_num = Column(Float, default=0.0, nullable=False)
    lock_num = Column(Float, default=0.0, nullable=False)
    used_num = Column(Float, default=0.0, nullable=False)
