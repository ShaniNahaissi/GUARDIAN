from __future__ import annotations

import time
import unittest

from bl.detection.metrics import ModelMetricsEvaluator, SystemMetricsTracker, compute_iou


class TestPerformanceMetrics(unittest.TestCase):
    def test_compute_iou(self):
        # 1. Perfect overlap
        box1 = (10, 10, 50, 50)
        self.assertAlmostEqual(compute_iou(box1, box1), 1.0)

        # 2. No overlap
        box2 = (60, 60, 100, 100)
        self.assertEqual(compute_iou(box1, box2), 0.0)

        # 3. Partial overlap (half width overlap)
        box3 = (10, 10, 30, 50)  # Area = 20 * 40 = 800
        box4 = (20, 10, 40, 50)  # Area = 20 * 40 = 800
        # Intersection = (30-20) * (50-10) = 10 * 40 = 400
        # Union = 800 + 800 - 400 = 1200
        # IoU = 400 / 1200 = 0.333333
        self.assertAlmostEqual(compute_iou(box3, box4), 1.0 / 3.0)

    def test_system_metrics_tracker(self):
        tracker = SystemMetricsTracker(window_size=5)
        # Record a frame and sleep briefly to simulate processing
        tracker.record_frame(12.5)
        time.sleep(0.05)
        tracker.record_frame(15.0)

        # Check average latency
        self.assertAlmostEqual(tracker.get_avg_latency(), 13.75)

        # Check FPS calculation
        fps = tracker.get_fps()
        self.assertTrue(fps > 0.0)

        # Check cpu utilization returns float
        cpu = tracker.get_cpu_utilization()
        self.assertIsInstance(cpu, float)

        # Check GPU VRAM query returns a tuple of ints
        vram_used, vram_total = tracker.get_gpu_vram()
        self.assertIsInstance(vram_used, int)
        self.assertIsInstance(vram_total, int)

    def test_model_metrics_evaluator(self):
        evaluator = ModelMetricsEvaluator()

        # Image 1 ground truth: 1 Gun [10, 10, 30, 30]
        # Image 1 prediction: 1 Gun [10, 10, 28, 28] score=0.9 (matches), 1 Gun [50, 50, 70, 70] score=0.8 (false positive)
        evaluator.add_image_results(
            gt_boxes=[(0, (10, 10, 30, 30))],
            pred_boxes=[
                (0, 0.9, (10, 10, 28, 28)),
                (0, 0.8, (50, 50, 70, 70)),
            ],
        )

        # Image 2 ground truth: 1 Knife [20, 20, 40, 40]
        # Image 2 prediction: 1 Knife [100, 100, 120, 120] score=0.9 (false positive, no GT overlap)
        # (Knife GT is unmatched/false negative)
        evaluator.add_image_results(
            gt_boxes=[(1, (20, 20, 40, 40))],
            pred_boxes=[(1, 0.9, (100, 100, 120, 120))],
        )

        # Evaluate at confidence threshold 0.35, IoU threshold 0.5
        metrics = evaluator.evaluate(conf_threshold=0.35, iou_threshold=0.5)

        # Class 0: 1 GT, 2 Pred (1 match, 1 FP)
        # Class 1: 1 GT, 1 Pred (0 match, 1 FP)
        # Total: TP=1, FP=2, FN=1
        # Precision = 1 / 3 = 0.3333
        # Recall = 1 / 2 = 0.5
        # F1 = 2 * (1/3) * (1/2) / (1/3 + 1/2) = 0.4
        self.assertAlmostEqual(metrics["precision"], 1.0 / 3.0, places=3)
        self.assertAlmostEqual(metrics["recall"], 0.5, places=3)
        self.assertAlmostEqual(metrics["f1_score"], 0.4, places=3)

        # Check mAP calculation output is float
        self.assertIsInstance(metrics["mAP_50"], float)
        self.assertIn("class_0", metrics["class_ap_50"])
        self.assertIn("class_1", metrics["class_ap_50"])


if __name__ == "__main__":
    unittest.main()
