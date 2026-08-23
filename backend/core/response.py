# -*- coding: utf-8 -*-
from typing import Any, Optional


def success(data: Any = None, msg: str = "操作成功") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "操作失败", code: int = -1, data: Any = None) -> dict:
    return {"code": code, "msg": msg, "data": data}


# 统一错误码
class Code:
    SUCCESS = 0
    FAIL = -1
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    PARAM_ERROR = 422
    BUSINESS_ERROR = 1000
