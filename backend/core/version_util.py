# -*- coding: utf-8 -*-
"""
语义化版本工具。版本号不要在代码里硬编码，统一用这里的常量。
- MAJOR：不兼容变更时手动 +1
- MINOR：向下兼容新增功能 +1，同时 PATCH 归零
- PATCH：小修小补 +1
"""

APP_VERSION_MAJOR = 1
APP_VERSION_MINOR = 2
APP_VERSION_PATCH = 2


def get_app_version() -> str:
    """返回 "X.Y.Z" 语义化版本字符串"""
    return f"{APP_VERSION_MAJOR}.{APP_VERSION_MINOR}.{APP_VERSION_PATCH}"


def parse_version(ver: str) -> tuple[int, int, int]:
    """解析 "X.Y.Z" 字符串为三元组，解析失败返回 (0,0,0)"""
    try:
        parts = str(ver).strip().split(".")
        if len(parts) != 3:
            return 0, 0, 0
        return int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, AttributeError):
        return 0, 0, 0
