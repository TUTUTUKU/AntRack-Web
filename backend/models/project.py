# -*- coding: utf-8 -*-
# models/project.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    status = Column(String(20), default="prepare", nullable=False)  # prepare/making/finish
    intro = Column(String(500), default="", nullable=False)
    link = Column(String(255), default="", nullable=False)

    create_time = Column(DateTime, default=datetime.now, nullable=False)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
