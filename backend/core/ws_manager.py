# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器：多端在线时广播冲突通知、阶段变更、恢复完成等事件。
任意一端处理冲突后，其它在线端立刻收到。
"""
from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime


class _Conn:
    def __init__(self, ws: WebSocket, who: str, peer: str):
        self.ws = ws
        self.who = who          # "user" 或 "device"
        self.peer = peer        # 用户名 或 device_id


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: list[_Conn] = []

    async def connect(self, ws: WebSocket, who: str, peer: str) -> None:
        await ws.accept()
        self._conns.append(_Conn(ws, who, peer))

    def disconnect(self, ws: WebSocket) -> None:
        self._conns = [c for c in self._conns if c.ws is not ws]

    async def _safe_send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    async def broadcast(self, event: str, data: dict) -> None:
        payload = {
            "event": event,
            "data": data,
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        for c in list(self._conns):
            await self._safe_send(c.ws, payload)

    # ---------------- 业务语义化广播 ----------------
    async def notify_conflict_created(self, conflict_ids: list[int], material_ids: list[int]):
        await self.broadcast("conflict:created", {
            "conflict_ids": conflict_ids,
            "material_ids": material_ids,
        })

    async def notify_conflict_resolved(self, conflict_id: int, material_id: int, status: str):
        await self.broadcast("conflict:resolved", {
            "conflict_id": conflict_id,
            "material_id": material_id,
            "status": status,  # "accepted" | "dismissed"
        })

    async def notify_stage_changed(self, new_global_check_code: int):
        await self.broadcast("stage:changed", {
            "new_global_check_code": new_global_check_code,
        })

    async def notify_restored(self, backup_snapshot_id: int | None, version: str):
        await self.broadcast("data:restored", {
            "backup_snapshot_id": backup_snapshot_id,
            "version": version,
        })


ws_mgr = ConnectionManager()
