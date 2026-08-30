# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class SnapshotOut(BaseModel):
    id: int
    trigger: str
    version: str = Field("0.0.0")
    file_path: str = ""
    file_size: int = 0
    note: str = ""
    create_time: str = ""
    expiry_time: str = ""

    class Config:
        from_attributes = True
