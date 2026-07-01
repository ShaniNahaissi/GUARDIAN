from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

import numpy as np

logger = logging.getLogger("guardian.metrics")

# ponytail: lazy-load psutil to keep startup lightweight and allow running without it
try:
    import psutil
except ImportError:
    psutil = None


class SystemMetricsTracker:
    """Tracks system resource utilization, frame rate (FPS), and inference latency."""
    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        self.frame_times: list[float] = []
        self.inference_latencies: list[float] = []
        self.last_cpu_query = 0.0
        self.cached_cpu = 0.0

    def record_frame(self, latency_ms: float) -> None:
        """Records frame processing timestamp and latency."""
        now = time.perf_counter()
        self.frame_times.append(now)
        self.inference_latencies.append(latency_ms)

        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
        if len(self.inference_latencies) > self.window_size:
            self.inference_latencies.pop(0)

    def get_fps(self) -> float:
        """Computes current throughput (FPS) over the window."""
        if len(self.frame_times) < 2:
            return 0.0
        elapsed = self.frame_times[-1] - self.frame_times[0]
        if elapsed <= 0:
            return 0.0
        return (len(self.frame_times) - 1) / elapsed

    def get_avg_latency(self) -> float:
        """Returns average latency in milliseconds over the window."""
        if not self.inference_latencies:
            return 0.0
        return sum(self.inference_latencies) / len(self.inference_latencies)

    def get_cpu_utilization(self) -> float:
        """Queries CPU usage percentage, cached to avoid blocking/overhead."""
        if psutil is None:
            return 0.0
        now = time.perf_counter()
        # ponytail: cache CPU query for 1 second to avoid blocking frequent frame loops
        if now - self.last_cpu_query > 1.0:
            self.cached_cpu = float(psutil.cpu_percent(interval=None))
            self.last_cpu_query = now
        return self.cached_cpu

    def get_gpu_vram(self) -> tuple[int, int]:
        """Queries NVIDIA GPU VRAM (used, total) in MB via nvidia-smi. Returns (0, 0) if unavailable."""
        try:
            # ponytail: run nvidia-smi directly via subprocess to avoid heavy dependencies (gputil, torch)
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            used, total = map(int, out.strip().split(","))
            return used, total
        except Exception:
            return 0, 0

    def get_all_metrics(self) -> dict[str, Any]:
        """Returns a snapshot of all system performance metrics."""
        used_vram, total_vram = self.get_gpu_vram()
        return {
            "fps": round(self.get_fps(), 2),
            "avg_latency_ms": round(self.get_avg_latency(), 2),
            "cpu_utilization_pct": self.get_cpu_utilization(),
            "gpu_vram_used_mb": used_vram,
            "gpu_vram_total_mb": total_vram,
        }


def compute_iou(box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]) -> float:
    """Computes Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


class ModelMetricsEvaluator:
    """Computes Precision, Recall, F1-Score, and mAP@50 over predictions and ground truths."""
    def __init__(self) -> None:
        # Structured list of ground truths: (image_id, class_id, [x1, y1, x2, y2])
        self.ground_truths: list[tuple[int, int, tuple[float, float, float, float]]] = []
        # Structured list of predictions: (image_id, class_id, score, [x1, y1, x2, y2])
        self.predictions: list[tuple[int, int, float, tuple[float, float, float, float]]] = []
        self.image_counter = 0

    def add_image_results(
        self,
        gt_boxes: list[tuple[int, tuple[float, float, float, float]]],
        pred_boxes: list[tuple[int, float, tuple[float, float, float, float]]],
    ) -> None:
        """Adds ground truth and prediction bounding boxes for a single image evaluation step."""
        img_id = self.image_counter
        self.image_counter += 1

        for class_id, bbox in gt_boxes:
            self.ground_truths.append((img_id, class_id, bbox))
        for class_id, score, bbox in pred_boxes:
            self.predictions.append((img_id, class_id, score, bbox))

    def evaluate(self, conf_threshold: float = 0.35, iou_threshold: float = 0.5) -> dict[str, Any]:
        """Computes evaluation metrics across all added images."""
        unique_classes = set(gt[1] for gt in self.ground_truths) | set(pred[1] for pred in self.predictions)
        class_aps: dict[int, float] = {}

        # 1. Compute mAP@50 per class
        for cid in unique_classes:
            # Filter gt and predictions for this class
            class_gts = [gt for gt in self.ground_truths if gt[1] == cid]
            class_preds = [pred for pred in self.predictions if pred[1] == cid]

            if not class_gts:
                class_aps[cid] = 0.0
                continue

            # Group ground truths by image_id for matching
            gt_by_img: dict[int, list[tuple[int, tuple[float, float, float, float], bool]]] = {}
            for gt_id, (_, _, bbox) in enumerate(class_gts):
                img_id = class_gts[gt_id][0]
                # Each entry: (gt_idx, bbox, matched_flag)
                gt_by_img.setdefault(img_id, []).append((gt_id, bbox, False))

            # Sort predictions by score descending
            class_preds = sorted(class_preds, key=lambda x: x[2], reverse=True)
            tp = np.zeros(len(class_preds))
            fp = np.zeros(len(class_preds))

            for p_idx, (img_id, _, _, p_box) in enumerate(class_preds):
                img_gts = gt_by_img.get(img_id, [])
                if not img_gts:
                    fp[p_idx] = 1.0
                    continue

                best_iou = -1.0
                best_gt_idx = -1

                for i, (gt_idx, gt_box, matched) in enumerate(img_gts):
                    if matched:
                        continue
                    iou = compute_iou(p_box, gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = i

                if best_iou >= iou_threshold and best_gt_idx != -1:
                    # Match found!
                    gt_idx, gt_box, _ = img_gts[best_gt_idx]
                    img_gts[best_gt_idx] = (gt_idx, gt_box, True)  # Mark matched
                    tp[p_idx] = 1.0
                else:
                    fp[p_idx] = 1.0

            # Calculate AP via precision-recall curve integration
            cum_tp = np.cumsum(tp)
            cum_fp = np.cumsum(fp)

            recalls = cum_tp / len(class_gts)
            precisions = cum_tp / np.maximum(cum_tp + cum_fp, 1e-16)

            # COCO/YOLO all-points interpolation area calculation
            mrec = np.concatenate(([0.0], recalls, [1.0]))
            mpre = np.concatenate(([0.0], precisions, [0.0]))
            for i in range(len(mpre) - 2, -1, -1):
                mpre[i] = max(mpre[i], mpre[i + 1])
            indices = np.where(mrec[1:] != mrec[:-1])[0]
            ap = np.sum((mrec[indices + 1] - mrec[indices]) * mpre[indices + 1])
            class_aps[cid] = float(ap)

        # 2. Compute Precision, Recall, F1-Score at conf_threshold
        filtered_preds = [p for p in self.predictions if p[2] >= conf_threshold]
        total_gt = len(self.ground_truths)

        # Track matches specifically at this confidence threshold
        tp_count = 0
        matched_gt_ids: set[int] = set()

        # Group all ground truths by image_id and class_id
        gt_lookup: dict[tuple[int, int], list[tuple[int, tuple[float, float, float, float]]]] = {}
        for gt_idx, (img_id, cid, bbox) in enumerate(self.ground_truths):
            gt_lookup.setdefault((img_id, cid), []).append((gt_idx, bbox))

        # Sort confidence-filtered predictions descending
        filtered_preds = sorted(filtered_preds, key=lambda x: x[2], reverse=True)
        for img_id, cid, _, p_box in filtered_preds:
            img_class_gts = gt_lookup.get((img_id, cid), [])
            best_iou = -1.0
            best_gt_idx = -1

            for gt_idx, gt_box in img_class_gts:
                if gt_idx in matched_gt_ids:
                    continue
                iou = compute_iou(p_box, gt_box)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = gt_idx

            if best_iou >= iou_threshold and best_gt_idx != -1:
                tp_count += 1
                matched_gt_ids.add(best_gt_idx)

        fp_count = len(filtered_preds) - tp_count
        fn_count = total_gt - tp_count

        precision = tp_count / max(tp_count + fp_count, 1)
        recall = tp_count / max(tp_count + fn_count, 1)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        mAP = sum(class_aps.values()) / max(len(class_aps), 1)

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "mAP_50": round(mAP, 4),
            "class_ap_50": {f"class_{cid}": round(ap, 4) for cid, ap in class_aps.items()},
        }


def log_metrics(
    metrics: dict[str, Any],
    step: int,
    log_dir: str | None = None,
    use_tb: bool = False,
    use_wandb: bool = False,
) -> None:
    """Logs metrics using structured JSON format, TensorBoard, or Weights & Biases."""
    msg = f"metrics_log step={step} metrics={json.dumps(metrics)}"
    logger.info(msg)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "metrics.jsonl")
        # ponytail: append JSON line to a simple jsonl file
        with open(log_file, "a") as f:
            f.write(json.dumps({"step": step, "timestamp": time.time(), **metrics}) + "\n")

    if use_tb:
        try:
            # ponytail: lazy-load tensorboard to avoid making it a hard requirement
            from torch.utils.tensorboard import SummaryWriter  # type: ignore
            writer = SummaryWriter(log_dir=log_dir)
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    writer.add_scalar(k, v, step)
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, (int, float)):
                            writer.add_scalar(f"{k}/{sub_k}", sub_v, step)
            writer.close()
        except ImportError:
            logger.warning("TensorBoard SummaryWriter not found. Skipping TB logging.")

    if use_wandb:
        try:
            # ponytail: lazy-load wandb to avoid making it a hard requirement
            import wandb  # type: ignore
            if wandb.run is not None:
                wandb.log(metrics, step=step)
            else:
                logger.warning("WandB run not initialized. Call wandb.init() first.")
        except ImportError:
            logger.warning("WandB not found. Skipping WandB logging.")
