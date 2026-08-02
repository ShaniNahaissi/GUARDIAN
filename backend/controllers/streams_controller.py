from __future__ import annotations

import asyncio
import logging
import time

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from bl.detection import state as det_state
from bl.detection.pipeline import process_frame_pipeline, remove_feature_extractor
from bl.detection.metrics import SystemMetricsTracker
from bl.detection.streaming import connection_manager, store
from bl.detection.tracker import remove_byte_tracker
from bl.metrics_service import save_metrics_to_db
from bl.rbac import CAMERAS_READ
from dependencies.security import require_permission
from models.user import User

logger = logging.getLogger("guardian.audit")

router = APIRouter(tags=["streams"])


@router.get("/api/streams/{stream_id}/meta")
async def stream_meta(stream_id: str, _user: User = Depends(require_permission(CAMERAS_READ))) -> JSONResponse:
    return JSONResponse(await store.get_meta(stream_id))


@router.websocket("/producer/{stream_id}")
async def producer_websocket(websocket: WebSocket, stream_id: str) -> None:
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info("stream.producer.connected stream_id=%s client=%s", stream_id, client_host)

    # Always start a new producer session with a completely clean tracking state.
    # If a producer reconnects with the same stream_id (e.g. after a brief disconnect),
    # the previous session's ByteTrack instance and TemporalFeatureExtractor may still
    # hold stale track IDs and ghost bounding boxes. Tearing them down here ensures
    # the new session's first frame is never contaminated by the old session's state.
    remove_byte_tracker(stream_id)
    remove_feature_extractor(stream_id)

    detector = det_state.detector
    if detector is None:
        logger.error("stream.producer.reject stream_id=%s reason=model_not_loaded", stream_id)
        await websocket.close(code=1011)
        return

    frame_count = 0
    metrics_tracker = SystemMetricsTracker()
    try:
        while True:
            payload = await websocket.receive_bytes()
            array = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning(
                    "stream.producer.decode_failed stream_id=%s payload_bytes=%s",
                    stream_id,
                    len(payload),
                )
                continue

            frame_count += 1
            start = time.perf_counter()
            try:
                jpeg_bytes, track_payload, detections = await asyncio.to_thread(
                    process_frame_pipeline,
                    stream_id,
                    frame,
                    detector,
                    det_state.person_detector,
                )
            except Exception:
                logger.exception("stream.producer.process_failed stream_id=%s frame=%s", stream_id, frame_count)
                continue

            process_ms = (time.perf_counter() - start) * 1000
            metrics_tracker.record_frame(process_ms)

            await store.update(stream_id, payload, jpeg_bytes, detections, track_payload["tracks"])
            await connection_manager.broadcast_frame(stream_id, jpeg_bytes, track_payload)

            asyncio.create_task(
                save_metrics_to_db(
                    stream_id=stream_id,
                    frame_seq=track_payload["frame_seq"],
                    total_latency_ms=process_ms,
                    yolo_latency_ms=track_payload.get("yolo_latency_ms", 0.0),
                    person_latency_ms=track_payload.get("person_latency_ms", 0.0),
                    action_latency_ms=track_payload.get("action_latency_ms", 0.0),
                    detections_count=len(detections),
                    track_count=len(track_payload["tracks"]),
                    detections_json=track_payload["tracks"],
                    cpu_utilization=metrics_tracker.get_cpu_utilization(),
                    gpu_vram_used=metrics_tracker.get_gpu_vram()[0],
                    evaluated_sequences=track_payload.get("evaluated_sequences", []),
                )
            )

            if frame_count % 30 == 0:
                stats = metrics_tracker.get_all_metrics()
                logger.info(
                    "stream.producer.frame stream_id=%s frame=%s input_bytes=%s output_bytes=%s tracks=%s process_ms=%.2f fps=%.2f cpu_pct=%.1f%% gpu_vram_used=%dMB",
                    stream_id,
                    frame_count,
                    len(payload),
                    len(jpeg_bytes),
                    len(track_payload["tracks"]),
                    process_ms,
                    stats["fps"],
                    stats["cpu_utilization_pct"],
                    stats["gpu_vram_used_mb"],
                )
    except WebSocketDisconnect:
        logger.info("stream.producer.disconnected stream_id=%s frames=%s", stream_id, frame_count)
    except Exception:
        logger.exception("stream.producer.error stream_id=%s frames=%s", stream_id, frame_count)
        raise
    finally:
        remove_byte_tracker(stream_id)
        remove_feature_extractor(stream_id)


@router.websocket("/consumer/{stream_id}")
async def consumer_websocket(websocket: WebSocket, stream_id: str) -> None:
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info("stream.consumer.ws_connected stream_id=%s client=%s", stream_id, client_host)
    await connection_manager.connect_consumer(stream_id, websocket)
    try:
        while True:
            message = await websocket.receive()
            mtype = message.get("type")
            if mtype == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect_consumer(stream_id, websocket)
        logger.info("stream.consumer.ws_disconnected stream_id=%s client=%s", stream_id, client_host)


@router.get("/consumer/{stream_id}/frame")
async def consumer_snapshot(stream_id: str) -> StreamingResponse:
    frame = await store.get_processed(stream_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="No processed frame for stream")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")
