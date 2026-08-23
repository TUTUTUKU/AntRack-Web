# -*- coding: utf-8 -*-
"""
鉴权依赖：支持管理员 (user token) 与 App 设备 (device token) 双通道。
- 管理员 token：payload {sub=username, type=user} → 查 User 表
- 设备 token：payload {device_id, type=device} → 返回 Principal 伪对象
现有路由全部用 `_: object = Depends(get_current_user)` 忽略返回值，
因此升级为双通道不破坏任何现有调用。
"""
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from core.security import decode_token
from models.user import User

# tokenUrl 仅作 Swagger 文档展示，实际登录走 /api/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@dataclass
class Principal:
    """鉴权主体：管理员返回 User，设备返回此轻量对象。
    两者都具备 .id / .username 属性，保证调用方一致。"""
    id: int
    username: str
    is_device: bool = False
    device_id: str = ""


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> object:
    """解析 Token 并返回当前主体（User 或 Principal）；未登录/无效抛 401"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type", "user")

    if token_type == "device":
        # App 设备通道：返回 Principal 伪对象
        device_id = payload.get("device_id", "unknown")
        return Principal(
            id=0,
            username=f"app:{device_id}",
            is_device=True,
            device_id=device_id,
        )

    # 管理员通道（默认 / 向后兼容无 type 的旧 token）
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证无效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
