# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import STATIC_DIR, STATIC_URL_PREFIX
from database import engine, Base
from init_db import init_db
from routers import api_router
from core.response import fail, success
from core.ws_manager import ws_mgr
from core.scheduler import AntrackScheduler
from core.version_util import get_app_version
from core.security import decode_token

app = FastAPI(
    title="蚁仓 Ant Rack System (ANS)",
    description=f"V{get_app_version()} · 制作者 TUTUTUKU · 项目编号 TK02",
    version=get_app_version(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount(STATIC_URL_PREFIX, StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    init_db()
    # 启动后台调度器：自动备份 + 过期清理
    AntrackScheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    AntrackScheduler.stop()


app.include_router(api_router)


# ========== WebSocket：冲突/阶段/恢复/配置 多端实时推送 ==========
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query("", description="管理员 token 或 App device_token，JWT Bearer"),
):
    # 鉴权：与 HTTP 一致，管理员 JWT 或设备 JWT 都可接入
    payload = None
    if token:
        token_clean = token[len("Bearer "):] if token.lower().startswith("bearer ") else token
        payload = decode_token(token_clean)
    if not payload:
        # 先 accept 再 close，兼容浏览器调试
        await websocket.accept()
        await websocket.close(code=1008, reason="未授权：请携带 token 参数")
        return

    who = "user" if payload.get("type") == "user" else "device"
    peer = payload.get("username") if who == "user" else payload.get("device_id") or ""

    await ws_mgr.connect(websocket, who=who, peer=peer)
    # 连接建立先推一次当前版本和阶段号
    try:
        from database import SessionLocal
        from models.global_stage import GlobalStage
        db = SessionLocal()
        try:
            row = db.query(GlobalStage).filter(GlobalStage.id == 1).first()
            code = row.global_check_code if row else 1
        finally:
            db.close()
        from datetime import datetime
        await websocket.send_text(
            __import__("json").dumps({
                "event": "hello",
                "data": {
                    "version": get_app_version(),
                    "global_check_code": code,
                    "who": who,
                    "peer": peer,
                },
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }, ensure_ascii=False)
        )
    except Exception:
        pass

    try:
        while True:
            # 只接收心跳 ping，忽略业务上行
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_mgr.disconnect(websocket)
    except Exception:
        ws_mgr.disconnect(websocket)


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content=fail(f"服务器内部错误：{str(exc)}", code=500),
    )


@app.get("/")
def root():
    ver = get_app_version()
    return {
        "code": 0,
        "msg": f"蚁仓 Ant Rack System V{ver} 后端服务运行中",
        "data": {"version": ver},
    }


@app.get("/api/health")
def health():
    """健康检查，前端可用于快速判断断网。"""
    return success({"ok": True, "version": get_app_version()})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
