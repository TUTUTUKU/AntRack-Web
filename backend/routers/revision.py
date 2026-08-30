# -*- coding: utf-8 -*-
"""版本与阶段号接口"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success, fail
from core.biz_common import get_global_check_code, fmt_dt
from core.version_util import get_app_version
from models.conflict import Conflict
from models.backup_snapshot import BackupSnapshot
from models.user_config import UserConfig

router = APIRouter()


@router.get("/info")
def revision_info(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    code = get_global_check_code(db)
    return success({
        "version": get_app_version(),
        "global_check_code": code,
        "server_time": fmt_dt(datetime.now()),
    })
