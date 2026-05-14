from __future__ import annotations

from typing import Any

import cv2
import numpy as np
import supervision as sv

from bl.detection.tracker import get_byte_tracker, next_frame_seq
from bl.detection.yolo import Detection, YoloOnnxDetector


def _safe_track_id(val: Any) -> int:
    if val is None:
        return -1
    try:
        f = float(val)
        if np.isnan(f):
            return -1
        return int(f)
    except (TypeError, ValueError):
        return -1


def process_frame_pipeline(
    stream_id: str,
    frame_bgr: np.ndarray,
    det: YoloOnnxDetector,
) -> tuple[bytes, dict[str, Any], list[Detection]]:
    """Runs ONNX inference, ByteTrack update, drawing, and JPEG encode (sync; call via asyncio.to_thread)."""
    detections = det.predict(frame_bgr)
    tracker = get_byte_tracker(stream_id)
    h, w = frame_bgr.shape[:2]

    if not detections:
        tracked = tracker.update_with_detections(sv.Detections.empty())
    else:
        xyxy = np.array([[*d.xyxy] for d in detections], dtype=np.float32)
        conf = np.array([d.score for d in detections], dtype=np.float32)
        cls = np.array([d.class_id for d in detections], dtype=np.int32)
        tracked = tracker.update_with_detections(sv.Detections(xyxy=xyxy, confidence=conf, class_id=cls))

    tracks_out: list[dict[str, Any]] = []
    if tracked.xyxy is not None and len(tracked.xyxy) > 0:
        tids = tracked.tracker_id
        confs = tracked.confidence
        classes = tracked.class_id
        for i in range(len(tracked.xyxy)):
            x1, y1, x2, y2 = map(int, tracked.xyxy[i].tolist())
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            tid = _safe_track_id(tids[i]) if tids is not None else -1
            score = float(confs[i]) if confs is not None else 0.0
            cid = int(classes[i]) if classes is not None else 0
            cname = det._label_for(cid)
            tracks_out.append(
                {
                    "track_id": tid,
                    "bbox": [x1, y1, x2, y2],
                    "class_name": cname,
                    "confidence": score,
                }
            )
            label = f"id{tid} {cname}:{score:.2f}"
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (30, 30, 255), 2)
            cv2.putText(
                frame_bgr,
                label,
                (x1, max(y1 - 10, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (30, 30, 255),
                1,
                cv2.LINE_AA,
            )

    ok, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("jpeg_encode_failed")

    seq = next_frame_seq(stream_id)
    payload: dict[str, Any] = {
        "stream_id": stream_id,
        "frame_seq": seq,
        "tracks": tracks_out,
    }
    return encoded.tobytes(), payload, detections
