# -*- coding: utf-8 -*-
"""路由聚合"""
from fastapi import APIRouter

from routers import auth, category, material, project, stock_log, export, dashboard, app, backup

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/api/auth", tags=["登录鉴权"])
api_router.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
api_router.include_router(category.router, prefix="/api/category", tags=["分类管理"])
api_router.include_router(material.router, prefix="/api/material", tags=["物料管理"])
api_router.include_router(project.router, prefix="/api/project", tags=["项目管理"])
api_router.include_router(stock_log.router, prefix="/api/stock-log", tags=["库存流水"])
api_router.include_router(export.router, prefix="/api/export", tags=["数据导出"])
api_router.include_router(app.router, prefix="/api/app", tags=["App设备激活"])
api_router.include_router(backup.router, prefix="/api/backup", tags=["数据备份与恢复"])
