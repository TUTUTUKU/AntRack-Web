# -*- coding: utf-8 -*-
"""备份快照表"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class BackupSnapshot(Base):
    __tablename__ = "backup_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String(20), default="manual", nullable=False)     # manual / auto / app
    version_x = Column(Integer, nullable=False)
    version_y = Column(Integer, nullable=False)
    version_z = Column(Integer, nullable=False)
    file_path = Column(String(255), default="", nullable=False)       # 相对于 backend 目录的相对路径
    file_size = Column(Integer, default=0, nullable=False)
    note = Column(String(200), default="", nullable=False)
    create_time = Column(DateTime, default=datetime.now, nullable=False)
    expiry_time = Column(DateTime, nullable=True)
