# -*- coding: utf-8 -*-
"""路由聚合"""
from fastapi import APIRouter

from routers import (
    auth, category, material, project, stock_log, export, dashboard,
    app as app_router, backup, revision, conflicts, operation_logs, user_configs,
    auto_backup,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/api/auth", tags=["登录鉴权"])
api_router.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
api_router.include_router(category.router, prefix="/api/category", tags=["分类管理"])
api_router.include_router(material.router, prefix="/api/material", tags=["物料管理"])
api_router.include_router(project.router, prefix="/api/project", tags=["项目管理"])
api_router.include_router(stock_log.router, prefix="/api/stock-log", tags=["库存流水"])
api_router.include_router(export.router, prefix="/api/export", tags=["数据导出"])
api_router.include_router(backup.router, prefix="/api/backup", tags=["数据备份与恢复"])
# V1.2 新增模块
api_router.include_router(revision.router, prefix="/api/revision", tags=["系统版本与阶段"])
api_router.include_router(conflicts.router, prefix="/api/conflicts", tags=["冲突处理"])
api_router.include_router(operation_logs.router, prefix="/api/operation-logs", tags=["操作日志"])
api_router.include_router(user_configs.router, prefix="/api/user-configs", tags=["用户配置"])
api_router.include_router(auto_backup.router, prefix="/api/auto-backup", tags=["自动备份配置"])
# App：激活心跳 + 握手 + 离线同步（共用 /api/app 前缀）
api_router.include_router(app_router.router, prefix="/api/app", tags=["App 设备与同步"])
