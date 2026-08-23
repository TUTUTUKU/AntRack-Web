# -*- coding: utf-8 -*-
"""激活码授权模型 —— AntRack App 售卖激活用
- 每个 App 安装后绑定一台设备（Android ID），一个激活码可以限制只绑定 1 台或 N 台（max_bindings）
- license_code 是发卡码，你卖一份就生成一条发客户
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base


class License(Base):
    __tablename__ = "license"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    license_code = Column(String(64), unique=True, nullable=False, index=True)
    device_id = Column(Text, default="", nullable=False)  # 空=未绑定；绑定后存 Android ID（分号分隔支持多台）
    max_bindings = Column(Integer, default=1, nullable=False)  # 最多允许绑定几台设备
    expire_at = Column(DateTime, nullable=False)              # 到期时间
    remark = Column(String(255), default="", nullable=False)  # 备注：购买客户/订单号
    create_time = Column(DateTime, default=datetime.now, nullable=False)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
