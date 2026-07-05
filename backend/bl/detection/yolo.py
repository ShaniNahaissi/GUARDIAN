from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from bl.detection.config import INPUT_SIZE
from bl.detection.providers import select_onnx_providers


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
        self.session = ort.InferenceSession(str(model_path), providers=providers)
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
        detections: list[Detection] = []
        if idxs is None or (hasattr(idxs, "__len__") and len(idxs) == 0):
            return detections

        for idx in np.asarray(idxs).flatten():
            x, y, bw, bh = boxes[int(idx)]
            cid = class_ids[int(idx)]
            detections.append(
                Detection(
                    xyxy=(x, y, x + bw, y + bh),
                    score=float(scores[int(idx)]),
                    label=self._label_for(cid),
                    class_id=cid,
                )
            )
        return detections

    def predict(self, frame_bgr: np.ndarray) -> list[Detection]:
        import time
        import logging
        logger = logging.getLogger("guardian.metrics")
        
        blob, scale, pad = self._preprocess(frame_bgr)
        
        t0 = time.perf_counter()
        output = self.session.run([self.output_name], {self.input_name: blob})[0]
        self.last_inference_ms = (time.perf_counter() - t0) * 1000
        
        # ponytail: log raw model run time at debug level for fine-grained profiling
        logger.debug("model.predict.raw_inference_ms %.2f", self.last_inference_ms)
        
        return self._postprocess(output, frame_bgr.shape[:2], scale, pad)
