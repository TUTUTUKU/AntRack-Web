# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(..., description="登录账号")
    password: str = Field(..., description="登录密码")


class LoginOut(BaseModel):
    token: str
    username: str


class ChangePasswordIn(BaseModel):
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少6位）")
