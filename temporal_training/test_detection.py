"""Plain assert-based regression test for detection.py's vectorized
YoloOnnxDetector._postprocess -- confirms it produces identical results to the original
per-row Python-loop implementation (kept here as a reference) on synthetic model output, so
the vectorization can't silently change detection behavior. Runs locally with no GPU/model
file needed -- constructs a YoloOnnxDetector without calling __init__ (which would need a
real .onnx file), since _postprocess/_label_for don't touch the ONNX session."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import numpy as np

from detection import YoloOnnxDetector  # noqa: E402


def _make_detector() -> YoloOnnxDetector:
    det = object.__new__(YoloOnnxDetector)
    det.class_names = {0: "Gun", 1: "Knife", 2: "Suspect"}
    return det


def _reference_postprocess(preds, orig_shape, scale, pad, conf_threshold=0.35, iou_threshold=0.45):
    """The ORIGINAL per-row Python-loop implementation, kept only as a regression oracle."""
    h, w = orig_shape
    boxes, scores, class_ids = [], [], []
    for row in preds:
        class_scores = row[4:]
        if class_scores.size == 0:
            continue
        cls_id = int(np.argmax(class_scores))
        score = float(class_scores[cls_id])
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
    out = []
    if idxs is None or (hasattr(idxs, "__len__") and len(idxs) == 0):
        return out
    for idx in np.asarray(idxs).flatten():
        idx = int(idx)
        x, y, bw_, bh_ = boxes[idx]
        out.append((x, y, x + bw_, y + bh_, round(scores[idx], 6), class_ids[idx]))
    return out


def test_postprocess_matches_reference_loop_80_class() -> None:
    rng = np.random.default_rng(0)
    n, num_classes = 500, 80  # mirrors the person detector's real (84, 8400)-shaped output
    cxcywh = rng.uniform(20, 600, size=(n, 4))
    class_scores = rng.uniform(0, 1, size=(n, num_classes)).astype(np.float32)
    preds = np.concatenate([cxcywh, class_scores], axis=1).astype(np.float32)
    orig_shape, scale, pad = (480, 640), 1.0, (0.0, 0.0)

    det = _make_detector()
    got = sorted(
        (d.xyxy[0], d.xyxy[1], d.xyxy[2], d.xyxy[3], round(d.score, 6), d.class_id)
        for d in det._postprocess(preds, orig_shape, scale, pad)
    )
    expected = sorted(_reference_postprocess(preds, orig_shape, scale, pad))

    assert got == expected
    assert len(got) > 0  # sanity: this random data should produce at least some detections


def test_postprocess_matches_reference_loop_3_class() -> None:
    rng = np.random.default_rng(1)
    n, num_classes = 300, 3  # mirrors the primary Gun/Knife/Suspect detector's output width
    cxcywh = rng.uniform(20, 600, size=(n, 4))
    class_scores = rng.uniform(0, 1, size=(n, num_classes)).astype(np.float32)
    preds = np.concatenate([cxcywh, class_scores], axis=1).astype(np.float32)
    orig_shape, scale, pad = (480, 640), 0.8, (10.0, 5.0)

    det = _make_detector()
    got = sorted(
        (d.xyxy[0], d.xyxy[1], d.xyxy[2], d.xyxy[3], round(d.score, 6), d.class_id)
        for d in det._postprocess(preds, orig_shape, scale, pad)
    )
    expected = sorted(_reference_postprocess(preds, orig_shape, scale, pad))
    assert got == expected


def test_postprocess_empty_when_all_below_threshold() -> None:
    det = _make_detector()
    preds = np.zeros((10, 4 + 3), dtype=np.float32)
    assert det._postprocess(preds, (480, 640), 1.0, (0.0, 0.0), conf_threshold=0.35) == []


if __name__ == "__main__":
    test_postprocess_matches_reference_loop_80_class()
    test_postprocess_matches_reference_loop_3_class()
    test_postprocess_empty_when_all_below_threshold()
    print("OK: all detection.py smoke tests passed")
