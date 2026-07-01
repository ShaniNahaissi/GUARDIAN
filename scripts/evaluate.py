#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Set up python path so that bl modules can be imported
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / "backend"))

from bl.detection.metrics import ModelMetricsEvaluator, SystemMetricsTracker, log_metrics
from bl.detection.yolo import YoloOnnxDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("guardian.evaluator")


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate GUARDIAN ONNX Model Performance")
    parser.add_argument(
        "--data_dir",
        type=str,
        required=True,
        help="Path to YOLO dataset root (should contain images/val and labels/val)",
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default=str(REPO_ROOT / "trained_model" / "guardian_backend_model.onnx"),
        help="Path to the ONNX model file",
    )
    parser.add_argument(
        "--names_path",
        type=str,
        default=str(REPO_ROOT / "trained_model" / "names.txt"),
        help="Path to class names definition file",
    )
    parser.add_argument(
        "--conf_thresh",
        type=float,
        default=0.35,
        help="Confidence threshold for evaluation",
    )
    parser.add_argument(
        "--iou_thresh",
        type=float,
        default=0.5,
        help="IoU threshold for metrics",
    )
    parser.add_argument(
        "--log_dir",
        type=str,
        default=str(REPO_ROOT / "runs" / "eval"),
        help="Directory to save output evaluation metrics",
    )
    parser.add_argument(
        "--use_tb",
        action="store_true",
        help="Log metrics to TensorBoard",
    )
    parser.add_argument(
        "--use_wandb",
        action="store_true",
        help="Log metrics to Weights & Biases (WandB)",
    )
    return parser.parse_args()


def load_names(names_path: str) -> dict[int, str]:
    if not os.path.exists(names_path):
        logger.warning("Names file %s not found. Using default mapping.", names_path)
        return {0: "Gun", 1: "Knife", 2: "Suspect"}
    with open(names_path, "r") as f:
        names = [line.strip() for line in f if line.strip()]
    return {i: name for i, name in enumerate(names)}


def main():
    args = parse_args()
    logger.info("Initializing evaluation...")
    logger.info("ONNX Model Path: %s", args.model_path)
    logger.info("Dataset Directory: %s", args.data_dir)

    # 1. Initialize Detector
    class_names = load_names(args.names_path)
    detector = YoloOnnxDetector(Path(args.model_path), class_names)

    # 2. Check Dataset Paths
    img_dir = Path(args.data_dir) / "images" / "val"
    lbl_dir = Path(args.data_dir) / "labels" / "val"

    if not img_dir.exists():
        # ponytail: fallback if flat directories are passed directly
        img_dir = Path(args.data_dir) / "images"
        lbl_dir = Path(args.data_dir) / "labels"

    if not img_dir.exists():
        logger.error("Images directory not found: %s", img_dir)
        sys.exit(1)

    image_paths = sorted(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
    if not image_paths:
        logger.error("No validation images found in: %s", img_dir)
        sys.exit(1)

    logger.info("Found %d images to evaluate.", len(image_paths))

    # 3. Initialize Trackers
    evaluator = ModelMetricsEvaluator()
    sys_tracker = SystemMetricsTracker(window_size=len(image_paths))

    # 4. Processing Loop
    processed_count = 0
    for img_path in image_paths:
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            logger.warning("Could not read image: %s. Skipping.", img_path)
            continue

        h, w = img.shape[:2]

        # Load ground truth labels in YOLO format
        lbl_path = lbl_dir / f"{img_path.stem}.txt"
        gt_boxes = []
        if lbl_path.exists():
            with open(lbl_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        try:
                            cid = int(parts[0])
                            cx, cy, bw, bh = map(float, parts[1:5])
                            # ponytail: convert normalized YOLO coordinates to absolute bounding box [x1, y1, x2, y2]
                            x1 = (cx - bw / 2) * w
                            y1 = (cy - bh / 2) * h
                            x2 = (cx + bw / 2) * w
                            y2 = (cy + bh / 2) * h
                            gt_boxes.append((cid, (x1, y1, x2, y2)))
                        except ValueError:
                            continue

        # Run model inference & measure latency
        start_time = time.perf_counter()
        detections = detector.predict(img)
        latency_ms = (time.perf_counter() - start_time) * 1000

        sys_tracker.record_frame(latency_ms)

        # Parse detections to evaluator format
        pred_boxes = []
        for det in detections:
            pred_boxes.append((det.class_id, det.score, det.xyxy))

        evaluator.add_image_results(gt_boxes, pred_boxes)
        processed_count += 1

        if processed_count % 50 == 0:
            logger.info("Processed %d / %d images...", processed_count, len(image_paths))

    # 5. Compute Final Metrics
    logger.info("Computing final evaluation metrics...")
    model_metrics = evaluator.evaluate(
        conf_threshold=args.conf_thresh, iou_threshold=args.iou_thresh
    )
    sys_metrics = sys_tracker.get_all_metrics()

    # Combine metrics
    results = {
        "evaluation_confidence_threshold": args.conf_thresh,
        "evaluation_iou_threshold": args.iou_thresh,
        "total_images_evaluated": processed_count,
        "model_performance": model_metrics,
        "system_infrastructure": sys_metrics,
    }

    # 6. Log and Print Results
    print("\n" + "=" * 50)
    print("                GUARDIAN EVALUATION RESULTS            ")
    print("=" * 50)
    print(f"Total Evaluated Images : {processed_count}")
    print(f"Model Precision        : {model_metrics['precision']:.4f}")
    print(f"Model Recall           : {model_metrics['recall']:.4f}")
    print(f"Model F1-Score         : {model_metrics['f1_score']:.4f}")
    print(f"Model mAP@50           : {model_metrics['mAP_50']:.4f}")
    print("-" * 50)
    print(f"Average Throughput     : {sys_metrics['fps']:.2f} FPS")
    print(f"Average Latency        : {sys_metrics['avg_latency_ms']:.2f} ms")
    print(f"Avg CPU Utilization    : {sys_metrics['cpu_utilization_pct']:.1f}%")
    if sys_metrics["gpu_vram_total_mb"] > 0:
        print(
            f"GPU VRAM Allocated     : {sys_metrics['gpu_vram_used_mb']} / {sys_metrics['gpu_vram_total_mb']} MB"
        )
    else:
        print("GPU VRAM               : N/A (CPU execution or nvidia-smi failed)")
    print("=" * 50 + "\n")

    # Save to file, TensorBoard, and WandB
    log_metrics(
        results,
        step=processed_count,
        log_dir=args.log_dir,
        use_tb=args.use_tb,
        use_wandb=args.use_wandb,
    )
    logger.info("Evaluation metrics successfully saved to %s", args.log_dir)


if __name__ == "__main__":
    main()
