# -*- coding: utf-8 -*-
"""
App 设备激活与心跳通道
- POST /api/app/activate：App 自行联网解锁后，提交设备信息换取 device_token
- POST /api/app/heartbeat：周期性心跳，验证激活态并返回剩余有效期

设计原则：
1. 激活真实性由 App 自行保证（activation_proof 非空即接受），服务器不计算激活码
2. device_token 是 30 天有效的 JWT（type=device），现有数据接口通过 get_current_user 自动放行
3. 心跳用于 App 侧主动检查激活态是否仍然有效（token 是否过期）
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.response import success, fail
from core.security import create_device_token, decode_token, DEVICE_TOKEN_EXPIRE_DAYS
from dependencies import get_current_user, Principal

router = APIRouter()


class ActivateIn(BaseModel):
    device_id: str = Field(..., min_length=1, description="设备唯一标识（App 自行生成，如安卓 Android ID）")
    device_name: str = Field("", description="设备名称（如 vivo X100）")
    activation_proof: str = Field(..., min_length=1, description="App 本地激活凭证（非空即接受，服务器不做激活码计算）")


class HeartbeatIn(BaseModel):
    device_token: str = Field(..., description="当前持有的设备令牌")


@router.post("/activate")
def activate(data: ActivateIn):
    """App 激活后换取 device_token。
    - 只要 activation_proof 非空即接受（App 自行联网解锁）
    - 返回 device_token（30 天有效）和过期时间
    """
    token, expires_at = create_device_token(
        device_id=data.device_id.strip(),
        device_name=data.device_name.strip(),
    )
    return success({
        "device_token": token,
        "expires_at": expires_at,
        "valid_days": DEVICE_TOKEN_EXPIRE_DAYS,
    }, "设备激活成功")


@router.post("/heartbeat")
def heartbeat(data: HeartbeatIn):
    """App 周期性心跳：检查 device_token 是否仍然有效。
    - 有效 → 返回剩余天数
    - 无效/过期 → 401，App 需重新走 activate 流程
    """
    payload = decode_token(data.device_token)
    if not payload:
        return fail("设备令牌无效或已过期，请重新激活", data={"valid": False})

    if payload.get("type") != "device":
        return fail("令牌类型不正确", data={"valid": False})

    exp = payload.get("exp")
    if not exp:
        return fail("令牌格式异常", data={"valid": False})

    remaining_seconds = exp - datetime.utcnow().timestamp()
    if remaining_seconds <= 0:
        return fail("设备令牌已过期，请重新激活", data={"valid": False})

    remaining_days = round(remaining_seconds / 86400, 1)
    return success({
        "valid": True,
        "expires_at": datetime.utcfromtimestamp(exp).isoformat(),
        "remaining_days": remaining_days,
    }, "设备激活态有效")


@router.get("/status")
def status_check(principal: object = Depends(get_current_user)):
    """通用鉴权状态检查：管理员 token 或设备 token 均可调用。
    App 可用它快速验证当前 token 是否被服务器接受（200=有效，401=无效）。
    """
    if isinstance(principal, Principal):
        return success({"type": "device", "device_id": principal.device_id}, "设备令牌有效")
    return success({"type": "user", "username": principal.username}, "管理员令牌有效")
