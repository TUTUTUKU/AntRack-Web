# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from dependencies import get_current_user
from core.security import create_access_token, verify_password, hash_password
from core.response import success, fail
from models.user import User
from models.license import License
from schemas.user import LoginIn, LoginOut, ChangePasswordIn
from schemas.license import VerifyLicenseIn

router = APIRouter()


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        return fail("账号或密码错误", code=401)
    token = create_access_token(user.username)
    return success({"token": token, "username": user.username}, "登录成功")


@router.get("/info")
def info(user: User = Depends(get_current_user)):
    return success({
        "id": user.id,
        "username": user.username,
    })


@router.post("/change-password")
def change_password(data: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(data.old_password, user.password_hash):
        return fail("原密码错误")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return success(msg="密码修改成功，请重新登录")


# ============ AntRack App 激活码校验（公开接口，不依赖登录） ============
@router.post("/verify-license")
def verify_license(data: VerifyLicenseIn, db: Session = Depends(get_db)):
    """校验激活码 + 设备绑定
    - 激活码不存在 / 已到期：返回 valid=false
    - 未绑定：自动把当前设备写入 device_id（第 1 台绑定）
    - 已绑定：
        * 当前 device_id 已在列表里 → 通过（老设备）
        * 不在列表里 → 若剩余绑定额度够（已绑定设备数 < max_bindings）则新增绑定；否则拒绝
    """
    code = data.license_code.strip().upper()
    lic = db.query(License).filter(License.license_code == code).first()
    if not lic:
        return fail("激活码不存在", data={"valid": False})

    # 1. 到期检查
    now = datetime.now()
    if lic.expire_at < now:
        return fail("激活码已过期", data={"valid": False, "expire_at": lic.expire_at.isoformat()})

    # 2. 设备绑定
    dev_id = data.device_id.strip()
    existing = [d for d in lic.device_id.split(";") if d]
    if dev_id in existing:
        # 已在绑定列表，直接通过
        pass
    else:
        if len(existing) >= lic.max_bindings:
            return fail(
                f"激活码已达到最大绑定台数（{lic.max_bindings}），无法在新设备使用。"
                f"如需迁移请联系客服解绑。",
                data={"valid": False, "expire_at": lic.expire_at.isoformat()},
            )
        # 新绑定
        existing.append(dev_id)
        lic.device_id = ";".join(existing)
        db.commit()

    return success(
        {
            "valid": True,
            "expire_at": lic.expire_at.isoformat(),
            "license_code": lic.license_code,
            "max_bindings": lic.max_bindings,
            "current_bindings": len([d for d in lic.device_id.split(";") if d]),
        },
        msg="激活成功",
    )
