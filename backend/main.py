from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

import cv2
import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

MODEL_PATH = Path(__file__).resolve().parent.parent / "trained_model" / "guardian_backend_model.onnx"
INPUT_SIZE = 640
logger = logging.getLogger("guardian.audit")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class CameraInfo(BaseModel):
    id: str
    name: str
    location: str
    status: str = Field(default="normal")
    statusText: str = Field(default="NORMAL")
    imageUrl: str = Field(default="")
    time: str = Field(default="")


class CameraCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    location: str = ""
    imageUrl: str | None = None
    stream_uuid: str | None = Field(default=None, alias="streamUuid")


class SystemStats(BaseModel):
    activeCameras: int
    activeOnline: int
    warningAlerts: int
    majorAlerts: int
    criticalAlerts: int


@dataclass
class Detection:
    xyxy: tuple[int, int, int, int]
    score: float
    label: str


class YoloOnnxDetector:
    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        shape = self.session.get_inputs()[0].shape
        if len(shape) == 4 and isinstance(shape[2], int):
            self.image_size = int(shape[2])
        else:
            self.image_size = INPUT_SIZE

    def _preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, tuple[float, float]]:
        h, w = image.shape[:2]
        scale = min(self.image_size / w, self.image_size / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))
        resized = cv2.resize(image, (nw, nh))
        canvas = np.full((self.image_size, self.image_size, 3), 114, dtype=np.uint8)
        pad_x = (self.image_size - nw) // 2
        pad_y = (self.image_size - nh) // 2
        canvas[pad_y : pad_y + nh, pad_x : pad_x + nw] = resized

        blob = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None, ...]
        return blob, scale, (pad_x, pad_y)

    def _postprocess(
        self,
        output: np.ndarray,
        orig_shape: tuple[int, int],
        scale: float,
        pad: tuple[float, float],
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
    ) -> list[Detection]:
        h, w = orig_shape
        preds = output
        if preds.ndim == 3:
            preds = preds[0]
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T
        if preds.shape[1] < 6:
            return []

        boxes: list[list[int]] = []
        scores: list[float] = []
        class_ids: list[int] = []

        for row in preds:
            objectness = float(row[4])
            class_scores = row[5:]
            if class_scores.size == 0:
                continue
            cls_id = int(np.argmax(class_scores))
            cls_conf = float(class_scores[cls_id])
            score = objectness * cls_conf
            if score < conf_threshold:
                continue

            cx, cy, bw, bh = map(float, row[:4])
            x1 = (cx - bw / 2 - pad[0]) / scale
            y1 = (cy - bh / 2 - pad[1]) / scale
            x2 = (cx + bw / 2 - pad[0]) / scale
            y2 = (cy + bh / 2 - pad[1]) / scale

            x1 = int(max(0, min(w - 1, x1)))
            y1 = int(max(0, min(h - 1, y1)))
            x2 = int(max(0, min(w - 1, x2)))
            y2 = int(max(0, min(h - 1, y2)))
            if x2 <= x1 or y2 <= y1:
                continue

            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(score)
            class_ids.append(cls_id)

        if not boxes:
            return []

        idxs = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
        detections: list[Detection] = []
        if len(idxs) == 0:
            return detections

        for idx in idxs.flatten():
            x, y, bw, bh = boxes[idx]
            detections.append(
                Detection(
                    xyxy=(x, y, x + bw, y + bh),
                    score=float(scores[idx]),
                    label=f"class_{class_ids[idx]}",
                )
            )
        return detections

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        blob, scale, pad = self._preprocess(frame_bgr)
        output = self.session.run([self.output_name], {self.input_name: blob})[0]
        return self._postprocess(output, frame_bgr.shape[:2], scale, pad)


class StreamStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.raw_frames: dict[str, bytes] = {}
        self.processed_frames: dict[str, bytes] = {}
        self.detection_meta: dict[str, dict[str, Any]] = {}

    async def update(self, stream_id: str, raw_frame: bytes, processed_frame: bytes, detections: list[Detection]) -> None:
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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global detector
    logger.info("startup.begin model_path=%s", MODEL_PATH)
    detector = YoloOnnxDetector(MODEL_PATH)
    logger.info("startup.ready model_loaded=%s", detector is not None)
    yield
    logger.info("shutdown.complete")


app = FastAPI(title="Guardian Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_latency_middleware(request: Request, call_next: Any) -> Any:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "-")
    path = request.url.path
    query = request.url.query
    full_path = f"{path}?{query}" if query else path

    logger.info(
        "request.start request_id=%s method=%s path=%s client=%s user_agent=%s",
        request_id,
        request.method,
        full_path,
        client_host,
        user_agent,
    )

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "request.end request_id=%s method=%s path=%s status=%s latency_ms=%.2f client=%s",
            request_id,
            request.method,
            full_path,
            500,
            latency_ms,
            client_host,
        )
        raise

    latency_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.end request_id=%s method=%s path=%s status=%s latency_ms=%.2f client=%s",
        request_id,
        request.method,
        full_path,
        response.status_code,
        latency_ms,
        client_host,
    )
    return response

store = StreamStore()
detector: YoloOnnxDetector | None = None
cameras: list[CameraInfo] = []

@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "model_loaded": detector is not None})


@app.get("/api/cameras", response_model=list[CameraInfo])
async def get_cameras() -> list[CameraInfo]:
    return cameras


@app.post("/api/cameras")
async def add_camera(payload: CameraCreateRequest) -> JSONResponse:
    stream_key = (payload.stream_uuid or "").strip()
    camera_id = stream_key if stream_key else f"CAM-{len(cameras) + 1:03d}"
    cameras.append(
        CameraInfo(
            id=camera_id,
            name=payload.name,
            location=payload.location or "",
            imageUrl=payload.imageUrl or "",
        )
    )
    return JSONResponse({"ok": True, "id": camera_id})


@app.get("/api/stats", response_model=SystemStats)
async def get_stats() -> SystemStats:
    warning = 0
    major = 0
    critical = 0

    for c in cameras:
        if c.status == "warning":
            warning += 1
        elif c.status == "major":
            major += 1
        elif c.status == "critical":
            critical += 1

    return SystemStats(
        activeCameras=len(cameras),
        activeOnline=len(cameras),
        warningAlerts=warning,
        majorAlerts=major,
        criticalAlerts=critical,
    )


@app.get("/api/streams/{stream_id}/meta")
async def stream_meta(stream_id: str) -> JSONResponse:
    return JSONResponse(await store.get_meta(stream_id))


@app.websocket("/sw/stream/{stream_id}")
async def producer_stream(websocket: WebSocket, stream_id: str) -> None:
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info("stream.producer.connected stream_id=%s client=%s", stream_id, client_host)
    if detector is None:
        logger.error("stream.producer.reject stream_id=%s reason=model_not_loaded", stream_id)
        await websocket.close(code=1011)
        return

    frame_count = 0
    try:
        while True:
            start = time.perf_counter()
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
            detections = detector.predict(frame)
            for det in detections:
                x1, y1, x2, y2 = det.xyxy
                cv2.rectangle(frame, (x1, y1), (x2, y2), (30, 30, 255), 2)
                cv2.putText(
                    frame,
                    f"{det.label}:{det.score:.2f}",
                    (x1, max(y1 - 10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (30, 30, 255),
                    1,
                    cv2.LINE_AA,
                )

            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not ok:
                logger.warning("stream.producer.encode_failed stream_id=%s frame=%s", stream_id, frame_count)
                continue

            await store.update(stream_id, payload, encoded.tobytes(), detections)
            if frame_count % 30 == 0:
                process_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "stream.producer.frame stream_id=%s frame=%s input_bytes=%s output_bytes=%s detections=%s process_ms=%.2f",
                    stream_id,
                    frame_count,
                    len(payload),
                    len(encoded),
                    len(detections),
                    process_ms,
                )
    except WebSocketDisconnect:
        logger.info("stream.producer.disconnected stream_id=%s frames=%s", stream_id, frame_count)
        return
    except Exception:
        logger.exception("stream.producer.error stream_id=%s frames=%s", stream_id, frame_count)
        raise


@app.get("/consumer/{stream_id}")
async def consumer_stream(stream_id: str) -> StreamingResponse:
    logger.info("stream.consumer.connected stream_id=%s", stream_id)

    async def frame_generator() -> Any:
        sent_count = 0
        while True:
            frame = await store.get_processed(stream_id)
            if frame is None:
                await asyncio.sleep(0.05)
                continue
            sent_count += 1
            if sent_count % 60 == 0:
                logger.info(
                    "stream.consumer.frame stream_id=%s sent=%s frame_bytes=%s",
                    stream_id,
                    sent_count,
                    len(frame),
                )
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(0.03)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/consumer/{stream_id}/frame")
async def consumer_snapshot(stream_id: str) -> StreamingResponse:
    frame = await store.get_processed(stream_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="No processed frame for stream")
    return StreamingResponse(iter([frame]), media_type="image/jpeg")
