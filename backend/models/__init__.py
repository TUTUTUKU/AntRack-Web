# -*- coding: utf-8 -*-
"""ORM 模型聚合，便于一次性导入建表"""
from models.user import User
from models.category import Category
from models.material import Material
from models.project import Project
from models.project_bom import ProjectBom
from models.stock_log import StockLog
from models.license import License
from models.user_config import UserConfig
from models.conflict import Conflict
from models.backup_snapshot import BackupSnapshot
from models.operation_log import OperationLog
from models.global_stage import GlobalStage
from models.auto_backup_config import AutoBackupConfig

__all__ = [
    "User", "Category", "Material", "Project", "ProjectBom", "StockLog", "License",
    "UserConfig", "Conflict", "BackupSnapshot", "OperationLog", "GlobalStage",
    "AutoBackupConfig",
]
