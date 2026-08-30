# -*- coding: utf-8 -*-
"""账号配置表：三级设置 Web-APP 双向同步。JSON 存 key-val；按账号隔离"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base


class UserConfig(Base):
    __tablename__ = "user_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, index=True)
    key = Column(String(64), nullable=False, index=True)
    value = Column(Text, default="", nullable=False)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __mapper_args__ = {"eager_defaults": True}
