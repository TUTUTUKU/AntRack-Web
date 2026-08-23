# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import STATIC_DIR, STATIC_URL_PREFIX
from database import engine, Base
from init_db import init_db
from routers import api_router
from core.response import fail

app = FastAPI(
    title="蚁仓 Ant Rack System (ANS)",
    description="V1.0 · 制作者 TUTUTUKU · 项目编号 TK01",
    version="1.0.0",
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


app.include_router(api_router)


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content=fail(f"服务器内部错误：{str(exc)}", code=500),
    )


@app.get("/")
def root():
    return {"code": 0, "msg": "蚁仓 Ant Rack System V1.0 后端服务运行中", "data": None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
