from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("guardian.audit")


class StreamStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.raw_frames: dict[str, bytes] = {}
        self.processed_frames: dict[str, bytes] = {}
        self.detection_meta: dict[str, dict[str, Any]] = {}

    async def update(self, stream_id: str, raw_frame: bytes, processed_frame: bytes, detections: list[Any]) -> None:
        async with self._lock:
            self.raw_frames[stream_id] = raw_frame
            self.processed_frames[stream_id] = processed_frame
            self.detection_meta[stream_id] = {
                "count": len(detections),
                "max_score": max((d.score for d in detections), default=0.0),
            }

    async def get_processed(self, stream_id: str) -> bytes | None:
        async with self._lock:
            return self.processed_frames.get(stream_id)

    async def get_meta(self, stream_id: str) -> dict[str, Any]:
        async with self._lock:
            return self.detection_meta.get(stream_id, {"count": 0, "max_score": 0.0})


class ConnectionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._consumers: dict[str, set[WebSocket]] = {}

    async def connect_consumer(self, stream_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._consumers.setdefault(stream_id, set()).add(websocket)

    async def disconnect_consumer(self, stream_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            bucket = self._consumers.get(stream_id)
            if bucket and websocket in bucket:
                bucket.discard(websocket)
                if not bucket:
                    self._consumers.pop(stream_id, None)

    async def broadcast_frame(self, stream_id: str, jpeg: bytes, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._consumers.get(stream_id, ()))
        dead: list[tuple[WebSocket, str]] = []
        for ws in sockets:
            try:
                await ws.send_bytes(jpeg)
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("stream.consumer.send_failed stream_id=%s err=%s", stream_id, exc)
                dead.append((ws, stream_id))
        for ws, sid in dead:
            await self.disconnect_consumer(sid, ws)


connection_manager = ConnectionManager()
store = StreamStore()
