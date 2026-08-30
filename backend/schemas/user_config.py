# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Any


class ConfigSetIn(BaseModel):
    key: str = Field(..., max_length=64)
    value: str = Field("", max_length=10000)


class ConfigBatchSetIn(BaseModel):
    items: dict = Field(default_factory=dict, description="{key:value}")


class ConfigOut(BaseModel):
    key: str
    value: str
    update_time: str = ""
