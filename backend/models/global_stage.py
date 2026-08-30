# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer
from database import Base


class GlobalStage(Base):
    # 全局阶段校验码：仅当发生批量物料/配置变更时 +1
    # （批量删除、批量导入、配置批量写入、项目完工结算等），单条普通修改不增加
    # 表中永远只有 1 行（id=1），客户端只读取不写入
    __tablename__ = "global_stage"

    id = Column(Integer, primary_key=True, default=1, nullable=False)
    global_check_code = Column(Integer, default=1, nullable=False)
