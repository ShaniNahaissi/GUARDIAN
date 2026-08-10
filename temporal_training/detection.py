"""Self-contained copies of the small pieces of Guardian's detection stack that
dataset_builder.py needs (ONNX detector wrapper, ByteTrack smoother, 12D feature
extractor). Copied verbatim/near-verbatim from backend/bl/detection/{config,class_names,
providers,yolo,tracker,temporal_action}.py so this whole temporal_training/ folder can be
copied to a training machine on its own -- no backend/ package needed there, only
trained_model/ (for the actual detector weights) alongside it.

The detector itself (trained_model/guardian_backend_model.onnx) is reused, not modified.
If backend/bl/detection/* changes, re-sync the relevant piece here by hand -- this is a
deliberate, small duplication in exchange for temporal_training/ having zero import
dependency on backend/.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

# --- config.py ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = _REPO_ROOT / "trained_model" / "guardian_backend_model.onnx"
NAMES_PATH = MODEL_PATH.parent / "names.txt"
INPUT_SIZE = 640

# Generic (COCO-pretrained, 80-class) YOLOv8s person detector -- supplements the primary
# Gun/Knife/Suspect detector, which may rarely fire its own "Suspect" class on footage
# outside its own training domain (e.g. UCF-Crime). Only COCO class 0 ("person") is used;
# see merge_person_detections below for how the two detectors' outputs are combined.
PERSON_MODEL_PATH = _REPO_ROOT / "trained_model" / "yolov8s_person.onnx"
PERSON_COCO_CLASS_ID = 0


# --- class_names.py -----------------------------------------------------------------------
def load_class_names() -> dict[int, str]:
    names: dict[int, str] = {}
    raw = os.environ.get("GUARDIAN_CLASS_NAMES", "").strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            key, val = part.split(":", 1)
            try:
                names[int(key.strip())] = val.strip()
            except ValueError:
                continue
    if NAMES_PATH.exists():
        for i, line in enumerate(NAMES_PATH.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if line:
                names.setdefault(i, line)
    return names


# --- providers.py -------------------------------------------------------------------------
def select_onnx_providers() -> list[str]:
    want_cuda = os.environ.get("GUARDIAN_ORT_CUDA", "1").strip().lower() not in ("0", "false", "no")
    available = ort.get_available_providers()
    providers: list[str] = []
    if want_cuda and "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    if "TensorrtExecutionProvider" in available and os.environ.get("GUARDIAN_ORT_TRT", "").strip() == "1":
        providers.append("TensorrtExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers


# --- yolo.py ------------------------------------------------------------------------------
@dataclass
class Detection:
    xyxy: tuple[int, int, int, int]
    score: float
    label: str
    class_id: int


class YoloOnnxDetector:
    def __init__(self, model_path: Path, class_names: dict[int, str] | None = None) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.class_names = class_names or {}
        providers = select_onnx_providers()
        sess_options = ort.SessionOptions()
        sess_options.log_severity_level = 3
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(str(model_path), sess_options=sess_options, providers=providers)
        self._providers_used = self.session.get_providers()
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        shape = self.session.get_inputs()[0].shape
        if len(shape) == 4 and isinstance(shape[2], int):
            self.image_size = int(shape[2])
        else:
            self.image_size = INPUT_SIZE

    def _label_for(self, cls_id: int) -> str:
        return self.class_names.get(cls_id, f"class_{cls_id}")

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
        """Vectorized candidate filtering (numpy, no per-row Python loop) -- with an
        80-class COCO output (8400 candidate boxes for the person detector), the original
        `for row in preds:` version spent most of its time in interpreted Python doing
        per-row argmax/threshold/box-math, dwarfing the actual ONNX forward pass on offline
        batch runs over many videos. Behaviorally identical to the original (verified in
        test_detection.py), just computed as array ops instead of a Python loop."""
        h, w = orig_shape
        # float64, matching the Python-float precision the original per-row loop computed in
        # -- float32 box math rounds differently often enough at int-truncation boundaries to
        # shift close NMS ties vs. the reference implementation.
        preds = output.astype(np.float64)
        if preds.ndim == 3:
            preds = preds[0]
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T
        if preds.shape[1] < 6:
            return []

        class_scores = preds[:, 4:]
        cls_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(class_scores.shape[0]), cls_ids]

        keep = scores >= conf_threshold
        if not np.any(keep):
            return []
        preds, scores, cls_ids = preds[keep], scores[keep], cls_ids[keep]

        cx, cy, bw, bh = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
        x1 = np.clip((cx - bw / 2 - pad[0]) / scale, 0, w - 1)
        y1 = np.clip((cy - bh / 2 - pad[1]) / scale, 0, h - 1)
        x2 = np.clip((cx + bw / 2 - pad[0]) / scale, 0, w - 1)
        y2 = np.clip((cy + bh / 2 - pad[1]) / scale, 0, h - 1)

        # Truncate to int BEFORE taking width/height -- int(a)-int(b) != int(a-b) in general,
        # and the reference loop truncates x1/y1/x2/y2 first (matched here for identical output).
        x1, y1, x2, y2 = x1.astype(int), y1.astype(int), x2.astype(int), y2.astype(int)

        valid = (x2 > x1) & (y2 > y1)
        if not np.any(valid):
            return []
        x1, y1, x2, y2 = x1[valid], y1[valid], x2[valid], y2[valid]
        scores, cls_ids = scores[valid], cls_ids[valid]

        boxes = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1).tolist()
        score_list = scores.astype(float).tolist()

        idxs = cv2.dnn.NMSBoxes(boxes, score_list, conf_threshold, iou_threshold)
        detections: list[Detection] = []
        if idxs is None or (hasattr(idxs, "__len__") and len(idxs) == 0):
            return detections

        for idx in np.asarray(idxs).flatten():
            idx = int(idx)
            x, y, bw_i, bh_i = boxes[idx]
            cid = int(cls_ids[idx])
            detections.append(
                Detection(
                    xyxy=(x, y, x + bw_i, y + bh_i),
                    score=float(score_list[idx]),
                    label=self._label_for(cid),
                    class_id=cid,
                )
            )
        return detections

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        blob, scale, pad = self._preprocess(frame_bgr)
        output = self.session.run([self.output_name], {self.input_name: blob})[0]
        return self._postprocess(output, frame_bgr.shape[:2], scale, pad)


def merge_person_detections(
    primary_detections: list[Detection],
    person_detections: list[Detection],
    iou_threshold: float = 0.5,
) -> list[Detection]:
    """Combines the primary Gun/Knife/Suspect detector's output with the generic person
    detector's "person" boxes (COCO class 0), remapped to Guardian's Suspect class_id=2.
    Overlapping suspect boxes (the same physical person picked up by both detectors) are
    de-duplicated via NMS so the tracker doesn't see two boxes for one person. Weapon
    detections (class_id 0/1) pass through untouched -- the person detector never produces
    those."""
    weapons = [d for d in primary_detections if d.class_id in (0, 1)]
    suspects = [d for d in primary_detections if d.class_id == 2]
    suspects += [
        Detection(xyxy=d.xyxy, score=d.score, label="Suspect", class_id=2)
        for d in person_detections
        if d.class_id == PERSON_COCO_CLASS_ID
    ]

    if len(suspects) <= 1:
        return weapons + suspects

    boxes = [[x1, y1, x2 - x1, y2 - y1] for (x1, y1, x2, y2) in (d.xyxy for d in suspects)]
    scores = [d.score for d in suspects]
    keep = cv2.dnn.NMSBoxes(boxes, scores, 0.0, iou_threshold)
    if keep is None or (hasattr(keep, "__len__") and len(keep) == 0):
        return weapons
    keep_idxs = np.asarray(keep).flatten()
    return weapons + [suspects[int(i)] for i in keep_idxs]


# --- tracker.py ---------------------------------------------------------------------------
class TrackState:
    """Manages the state history of a single tracked object for temporal features."""

    def __init__(self, track_id: int, class_id: int, bbox: list[int], score: float) -> None:
        self.track_id = track_id
        self.class_id = class_id
        self.bbox_history: list[list[int]] = [bbox]
        self.score_history: list[float] = [score]
        self.missed_frames = 0
        self.total_detections = 1
        self.latest_bbox = bbox

    def update(self, bbox: list[int], score: float) -> None:
        self.latest_bbox = bbox
        self.bbox_history.append(bbox)
        if len(self.bbox_history) > 35:
            self.bbox_history.pop(0)
        self.score_history.append(score)
        if len(self.score_history) > 35:
            self.score_history.pop(0)
        self.missed_frames = 0
        self.total_detections += 1

    def get_latest_bbox(self) -> list[int]:
        return self.latest_bbox

    def get_latest_score(self) -> float:
        return self.score_history[-1] if self.score_history else 0.0


class StreamTrackSmoother:
    """Wraps supervision.ByteTrack with responsive state management + ghost-track handling."""

    def __init__(self, stream_id: str) -> None:
        import supervision as sv

        self.stream_id = stream_id
        self.tracker = sv.ByteTrack()
        self.active_tracks: dict[int, TrackState] = {}
        self.prev_boxes: dict[int, list[int]] = {}
        self.lock = threading.Lock()

    def smooth_box(self, track_id: int, raw_box: list[int], alpha: float = 0.60) -> list[int]:
        """Applies exponential moving average (EMA) coordinate smoothing to bounding boxes
        as shown in Code Snippet 3.2 of the project book."""
        if track_id not in self.prev_boxes:
            self.prev_boxes[track_id] = raw_box
            return raw_box
        prev = self.prev_boxes[track_id]
        smoothed = [
            int(alpha * raw + (1.0 - alpha) * p)
            for raw, p in zip(raw_box, prev)
        ]
        self.prev_boxes[track_id] = smoothed
        return smoothed

    def update_with_detections(self, detections) -> list[dict[str, Any]]:
        with self.lock:
            tracked = self.tracker.update_with_detections(detections)
            seen_tids = set()

            if tracked.xyxy is not None and len(tracked.xyxy) > 0:
                tids = tracked.tracker_id
                confs = tracked.confidence
                classes = tracked.class_id
                for i in range(len(tracked.xyxy)):
                    x1, y1, x2, y2 = map(int, tracked.xyxy[i].tolist())
                    tid = int(tids[i]) if tids is not None else -1
                    score = float(confs[i]) if confs is not None else 1.0
                    cid = int(classes[i]) if classes is not None else 0

                    if tid == -1:
                        continue

                    seen_tids.add(tid)
                    if tid in self.active_tracks:
                        self.active_tracks[tid].update([x1, y1, x2, y2], score)
                    else:
                        self.active_tracks[tid] = TrackState(tid, cid, [x1, y1, x2, y2], score)

            dead_tids = []
            for tid, state in self.active_tracks.items():
                if tid not in seen_tids:
                    state.missed_frames += 1
                    # Suspects (class 2) survive 1 missed frame, weapons (0/1) survive 0
                    max_missed = 1 if state.class_id == 2 else 0
                    if state.missed_frames <= max_missed:
                        decayed_score = state.get_latest_score() * 0.7
                        state.score_history.append(decayed_score)
                    else:
                        dead_tids.append(tid)

            for tid in dead_tids:
                self.active_tracks.pop(tid, None)

            tracks_out = []
            for tid, state in self.active_tracks.items():
                tracks_out.append({
                    "track_id": tid,
                    "bbox": state.get_latest_bbox(),
                    "class_id": state.class_id,
                    "confidence": state.get_latest_score(),
                    "missed_frames": state.missed_frames,
                })
            return tracks_out


_tracker_lock = threading.Lock()
_byte_trackers: dict[str, StreamTrackSmoother] = {}


def get_byte_tracker(stream_id: str) -> StreamTrackSmoother:
    with _tracker_lock:
        if stream_id not in _byte_trackers:
            _byte_trackers[stream_id] = StreamTrackSmoother(stream_id)
        return _byte_trackers[stream_id]


def remove_byte_tracker(stream_id: str) -> None:
    with _tracker_lock:
        _byte_trackers.pop(stream_id, None)


# --- temporal_action.py (feature extractor only; classifier lives in model.py) ------------
# Stabbing was dropped: UCF-Crime (this pipeline's data source) has no matching category and
# no other real data source is planned for it, so it would only ever ship untrained. Kept in
# sync with backend/bl/detection/temporal_action.py's ACTION_CLASSES.
ACTION_CLASSES = {
    0: "Normal",
    1: "Shooting",
    2: "Violence",
}


class TemporalFeatureExtractor:
    """Compiles track histories and computes multi-frame 12D feature vectors per suspect track."""

    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        self.history: dict[int, list[dict[str, Any]]] = {}

    def update_and_extract(
        self,
        active_tracks: list[dict[str, Any]],
        frame_shape: tuple[int, int],
        frame_seq: int,
    ) -> dict[int, np.ndarray]:
        h, w = frame_shape
        tids = {t["track_id"] for t in active_tracks}

        dead_ids = [tid for tid in self.history if tid not in tids]
        for tid in dead_ids:
            self.history.pop(tid, None)

        for t in active_tracks:
            tid = t["track_id"]
            self.history.setdefault(tid, []).append({
                "bbox": t["bbox"],
                "class_id": t["class_id"],
                "confidence": t["confidence"],
                "frame_seq": frame_seq,
            })
            if len(self.history[tid]) > self.window_size:
                self.history[tid].pop(0)

        sequences: dict[int, np.ndarray] = {}
        weapon_tracks = [t for t in active_tracks if t["class_id"] in (0, 1)]
        suspect_tracks = [t for t in active_tracks if t["class_id"] == 2]

        for suspect in suspect_tracks:
            tid = suspect["track_id"]
            track_hist = self.history.get(tid, [])
            if not track_hist:
                continue

            seq_features = []
            hist_len = len(track_hist)
            for idx in range(self.window_size):
                hist_idx = max(0, idx - (self.window_size - hist_len))
                state = track_hist[hist_idx]

                x1, y1, x2, y2 = state["bbox"]
                nx1, ny1, nx2, ny2 = x1 / w, y1 / h, x2 / w, y2 / h

                if hist_idx > 0:
                    prev_state = track_hist[hist_idx - 1]
                    px1, py1, px2, py2 = prev_state["bbox"]
                    dx1 = (x1 - px1) / w
                    dy1 = (y1 - py1) / h
                    dx2 = (x2 - px2) / w
                    dy2 = (y2 - py2) / h
                else:
                    dx1 = dy1 = dx2 = dy2 = 0.0

                conf = state["confidence"]

                min_dist_weapon = 1.0
                overlap_weapon = 0.0
                s_cx, s_cy = (x1 + x2) / 2, (y1 + y2) / 2
                for weapon in weapon_tracks:
                    wx1, wy1, wx2, wy2 = weapon["bbox"]
                    w_cx, w_cy = (wx1 + wx2) / 2, (wy1 + wy2) / 2
                    dist = (((s_cx - w_cx) / w) ** 2 + ((s_cy - w_cy) / h) ** 2) ** 0.5
                    min_dist_weapon = min(min_dist_weapon, dist)

                    ix1 = max(x1, wx1)
                    iy1 = max(y1, wy1)
                    ix2 = min(x2, wx2)
                    iy2 = min(y2, wy2)
                    if ix2 > ix1 and iy2 > iy1:
                        overlap_weapon = 1.0

                min_dist_suspect = 1.0
                for other in suspect_tracks:
                    if other["track_id"] == tid:
                        continue
                    ox1, oy1, ox2, oy2 = other["bbox"]
                    o_cx, o_cy = (ox1 + ox2) / 2, (oy1 + oy2) / 2
                    dist = (((s_cx - o_cx) / w) ** 2 + ((s_cy - o_cy) / h) ** 2) ** 0.5
                    min_dist_suspect = min(min_dist_suspect, dist)

                feat = [
                    nx1, ny1, nx2, ny2,
                    dx1, dy1, dx2, dy2,
                    conf,
                    min_dist_weapon,
                    min_dist_suspect,
                    overlap_weapon,
                ]
                seq_features.append(feat)

            sequences[tid] = np.array(seq_features, dtype=np.float32)

        return sequences
