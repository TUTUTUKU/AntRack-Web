# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 设备令牌有效期：30 天（App 周期性心跳续期）
DEVICE_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    """管理员 JWT：payload {sub, exp, type=user}"""
    minutes = expires_minutes if expires_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    to_encode = {"sub": subject, "exp": expire, "type": "user"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_device_token(device_id: str, device_name: str = "", expires_days: Optional[int] = None) -> tuple:
    """App 设备 JWT：payload {device_id, device_name, exp, type=device}
    返回 (token, expires_at_isoformat)
    """
    days = expires_days if expires_days is not None else DEVICE_TOKEN_EXPIRE_DAYS
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode = {"device_id": device_id, "device_name": device_name, "exp": expire, "type": "device"}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire.isoformat()


def decode_token(token: str) -> Optional[dict]:
    """通用 token 解析：返回 payload dict，失败返回 None。
    调用方通过 payload.get('type') 区分 user / device。
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[str]:
    """管理员 token 专用：返回 username，非 user 类型返回 None（向后兼容现有调用）"""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type", "user") != "user":
        return None
    return payload.get("sub")
