# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class VerifyLicenseIn(BaseModel):
    license_code: str = Field(..., min_length=4, max_length=64, description="用户输入的激活码")
    device_id: str = Field(..., min_length=1, max_length=512, description="App 端上报的设备 Android ID")


class VerifyLicenseOut(BaseModel):
    valid: bool
    expire_at: str | None = None
    message: str | None = None
