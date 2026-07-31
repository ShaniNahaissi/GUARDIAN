from __future__ import annotations

import logging
import threading
import time
from typing import Any

import cv2
import numpy as np
import supervision as sv

from bl.detection.tracker import get_byte_tracker, next_frame_seq
from bl.detection.yolo import Detection, YoloOnnxDetector
from bl.detection.temporal_action import NumPyCNNClassifier, TemporalFeatureExtractor, ACTION_CLASSES
from bl.detection.metrics import compute_iou

# Minimum box overlap to consider a raw weapon detection the same object as a ByteTrack-confirmed
# weapon track this frame, so its real persistent track_id can be reused instead of a placeholder.
_WEAPON_TRACK_MATCH_IOU = 0.3

logger = logging.getLogger("guardian.pipeline")

# Instantiate global shared action classifier
_action_classifier = NumPyCNNClassifier()
_feature_extractors: dict[str, TemporalFeatureExtractor] = {}
_extractor_lock = threading.Lock()


def get_feature_extractor(stream_id: str) -> TemporalFeatureExtractor:
    with _extractor_lock:
        if stream_id not in _feature_extractors:
            _feature_extractors[stream_id] = TemporalFeatureExtractor()
        return _feature_extractors[stream_id]


def remove_feature_extractor(stream_id: str) -> None:
    with _extractor_lock:
        _feature_extractors.pop(stream_id, None)


def _should_trigger_action_recognition(detections: list[Detection], frame_shape: tuple[int, int]) -> bool:
    """Early-exit checker: only run the CNN action classifier if weapons exist or multiple suspects are in close
    proximity. Takes this frame's raw detections (not the tracked/confirmed list) -- ByteTrack can take several
    frames to confirm a new track, which would otherwise delay/suppress triggering on a weapon that's genuinely
    visible right now."""
    h, w = frame_shape

    # 1. Trigger if any weapon class is present (class_id 0: Gun, 1: Knife)
    has_weapon = any(d.class_id in (0, 1) for d in detections)
    if has_weapon:
        return True

    # 2. Trigger if multiple suspects (class_id 2) are in close proximity (<35% of frame width/height or overlapping)
    suspect_tracks = [d for d in detections if d.class_id == 2]
    if len(suspect_tracks) >= 2:
        for i in range(len(suspect_tracks)):
            s1 = suspect_tracks[i]
            x1_1, y1_1, x2_1, y2_1 = s1.xyxy
            cx1, cy1 = (x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2

            for j in range(i + 1, len(suspect_tracks)):
                s2 = suspect_tracks[j]
                x1_2, y1_2, x2_2, y2_2 = s2.xyxy
                cx2, cy2 = (x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2
                
                # Center-to-center distance normalized by frame dimensions
                dist = (((cx1 - cx2) / w) ** 2 + ((cy1 - cy2) / h) ** 2) ** 0.5
                if dist < 0.35:
                    return True
                    
                # Bbox intersection check
                ix1 = max(x1_1, x1_2)
                iy1 = max(y1_1, y1_2)
                ix2 = min(x2_1, x2_2)
                iy2 = min(y2_1, y2_2)
                if ix2 > ix1 and iy2 > iy1:
                    return True
                    
    return False


def _merge_detections(
    weapon_detections: list[Detection],
    person_detections: list[Detection],
    suspect_label: str,
) -> list[Detection]:
    """Keeps only weapon classes (0: Gun, 1: Knife) from the custom model, and remaps
    the pretrained person model's COCO `person` class (0) to Guardian's Suspect class (2)."""
    weapons = [d for d in weapon_detections if d.class_id in (0, 1)]
    people = [
        Detection(xyxy=d.xyxy, score=d.score, label=suspect_label, class_id=2)
        for d in person_detections
        if d.class_id == 0
    ]
    return weapons + people


def process_frame_pipeline(
    stream_id: str,
    frame_bgr: np.ndarray,
    det: YoloOnnxDetector,
    person_det: YoloOnnxDetector | None = None,
) -> tuple[bytes, dict[str, Any], list[Detection]]:
    """Runs optimized ONNX inference, ByteTrack updates, temporal action classification, and broadcasts updates."""
    t_start = time.perf_counter()
    seq = next_frame_seq(stream_id)

    weapon_detections = det.predict(frame_bgr)
    person_detections = person_det.predict(frame_bgr) if person_det is not None else []
    detections = _merge_detections(weapon_detections, person_detections, det._label_for(2))
    tracker = get_byte_tracker(stream_id)
    h, w = frame_bgr.shape[:2]

    # Convert detector outputs to supervision format and run tracking update
    if not detections:
        tracked_list = tracker.update_with_detections(sv.Detections.empty())
    else:
        xyxy = np.array([[*d.xyxy] for d in detections], dtype=np.float32)
        conf = np.array([d.score for d in detections], dtype=np.float32)
        cls = np.array([d.class_id for d in detections], dtype=np.int32)
        tracked_list = tracker.update_with_detections(sv.Detections(xyxy=xyxy, confidence=conf, class_id=cls))

    # Evaluate early-exit triggering logic
    run_action_classifier = _should_trigger_action_recognition(detections, (h, w))
    
    extractor = get_feature_extractor(stream_id)
    # update histories (always done to maintain temporal trace consistency)
    sequences = extractor.update_and_extract(tracked_list, (h, w), seq)
    
    predicted_actions: dict[int, tuple[str, float]] = {}
    evaluated_sequences: list[dict[str, Any]] = []
    action_latency_ms = 0.0
    if run_action_classifier:
        # Run temporal inference over suspect sequences
        for tid, seq_feat in sequences.items():
            # 1. Displacement filter: compute displacement between start and end of sequence
            c1_x = (seq_feat[0][0] + seq_feat[0][2]) / 2
            c1_y = (seq_feat[0][1] + seq_feat[0][3]) / 2
            c2_x = (seq_feat[-1][0] + seq_feat[-1][2]) / 2
            c2_y = (seq_feat[-1][1] + seq_feat[-1][3]) / 2
            displacement = ((c1_x - c2_x) ** 2 + (c1_y - c2_y) ** 2) ** 0.5

            # Static check: displacement < 2% of frame size defaults to Normal
            if displacement < 0.02:
                action_label = "Normal"
                score = 1.0
            else:
                t_action = time.perf_counter()
                action_idx, score = _action_classifier.predict(seq_feat)
                action_latency_ms += (time.perf_counter() - t_action) * 1000
                action_label = ACTION_CLASSES.get(action_idx, "Normal")
            
            # 2. Confidence filtering: Only override class name if threat confidence is high (>= 70%)
            if action_label != "Normal" and score >= 0.70:
                predicted_actions[tid] = (action_label, score)
                logger.warning(
                    "threat_alert detected stream_id=%s track_id=%d action=%s confidence=%.2f%%",
                    stream_id, tid, action_label, score * 100
                )
            else:
                predicted_actions[tid] = ("Normal", 1.0)

            # Compile sequence analysis
            track_hist = extractor.history.get(tid, [])
            best_frame_seq = seq
            best_frame_score = 0.0
            if track_hist:
                best_state = max(track_hist, key=lambda x: x["confidence"])
                best_frame_seq = best_state["frame_seq"]
                best_frame_score = best_state["confidence"]
                
            evaluated_sequences.append({
                "track_id": tid,
                "start_frame_seq": track_hist[0]["frame_seq"] if track_hist else seq,
                "end_frame_seq": seq,
                "action_label": action_label if (action_label != "Normal" and score >= 0.70) else "Normal",
                "action_confidence": score if (action_label != "Normal" and score >= 0.70) else 1.0,
                "best_frame_seq": best_frame_seq,
                "best_frame_score": best_frame_score,
            })

    # Format tracks payload output
    tracks_out: list[dict[str, Any]] = []
    for t in tracked_list:
        tid = t["track_id"]
        cid = t["class_id"]
        score = t["confidence"]

        # Weapons are handled in the block below, straight from this frame's raw detections --
        # skip them here so a ByteTrack-confirmed weapon doesn't get added twice.
        if cid in (0, 1):
            continue

        x1, y1, x2, y2 = t["bbox"]

        # Ensure coordinates are within frame boundary
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)

        # Get label from detector mapping
        cname = det._label_for(cid)

        # Override class label & score for Suspects if active threat is classified
        if cid == 2 and tid in predicted_actions:
            action_label, action_score = predicted_actions[tid]
            if action_label != "Normal":
                cname = f"Suspect ({action_label})"
                score = action_score

        tracks_out.append(
            {
                "track_id": tid,
                "bbox": [x1, y1, x2, y2],
                "class_name": cname,
                "confidence": score,
            }
        )

    # Weapons are shown straight from this frame's raw detections, not the tracked/confirmed list --
    # ByteTrack can take several frames to confirm a new track (or drop it entirely if the box jitters),
    # which would otherwise hide a weapon that's genuinely visible right now. Suspects still go through
    # the tracker above since action recognition needs their persistent track_id across frames.
    #
    # Still reuse ByteTrack's own id when it has a confirmed weapon track overlapping this box, so the
    # displayed id is a real persistent identity whenever the tracker has one -- falling back to a
    # per-frame placeholder (negative, not persistent) only for weapons ByteTrack hasn't confirmed yet.
    tracked_weapons = [t for t in tracked_list if t["class_id"] in (0, 1)]
    next_placeholder_id = -1
    for d in detections:
        if d.class_id not in (0, 1):
            continue

        matched_tid: int | None = None
        best_iou = _WEAPON_TRACK_MATCH_IOU
        for t in tracked_weapons:
            iou = compute_iou(tuple(d.xyxy), tuple(t["bbox"]))
            if iou >= best_iou:
                best_iou = iou
                matched_tid = t["track_id"]

        if matched_tid is None:
            matched_tid = next_placeholder_id
            next_placeholder_id -= 1

        x1, y1, x2, y2 = d.xyxy
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        tracks_out.append(
            {
                "track_id": matched_tid,
                "bbox": [x1, y1, x2, y2],
                "class_name": det._label_for(d.class_id),
                "confidence": d.score,
            }
        )

    # Encode processed frame to JPEG
    ok, encoded = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("jpeg_encode_failed")

    pipeline_latency = (time.perf_counter() - t_start) * 1000

    payload: dict[str, Any] = {
        "stream_id": stream_id,
        "frame_seq": seq,
        "tracks": tracks_out,
        # Per-model breakdown so the admin dashboard can plot each model's own cost, not just
        # a combined "YOLO" figure -- yolo_latency_ms is the primary weapon detector alone.
        "yolo_latency_ms": getattr(det, "last_inference_ms", 0.0),
        "person_latency_ms": getattr(person_det, "last_inference_ms", 0.0) if person_det is not None else 0.0,
        "action_latency_ms": action_latency_ms,
        "pipeline_latency_ms": pipeline_latency,
        "evaluated_sequences": evaluated_sequences,
    }
    return encoded.tobytes(), payload, detections
