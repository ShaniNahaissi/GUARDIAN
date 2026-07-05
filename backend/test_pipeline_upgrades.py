from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add backend directory to path so that bl can be imported
sys.path.append(str(Path(__file__).resolve().parent))

import numpy as np
import supervision as sv

from bl.detection.augmentation import (
    MotionBlur,
    DigitalNoise,
    PerspectiveDistortion,
    OcclusionSimulation,
    VideoStyleAugmentor
)
from bl.detection.tracker import StreamTrackSmoother
from bl.detection.temporal_action import TemporalFeatureExtractor, NumPyGRUClassifier
from bl.detection.pipeline import _should_trigger_action_recognition


class TestPipelineUpgrades(unittest.TestCase):
    def test_augmentations(self):
        # Create dummy image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        
        # Test individual augmentations
        blur = MotionBlur(max_kernel_size=5)
        img_blur = blur(image)
        self.assertEqual(img_blur.shape, image.shape)
        
        noise = DigitalNoise(mode="gaussian")
        img_noise = noise(image)
        self.assertEqual(img_noise.shape, image.shape)
        
        noise_sp = DigitalNoise(mode="sp")
        img_noise_sp = noise_sp(image)
        self.assertEqual(img_noise_sp.shape, image.shape)
        
        distortion = PerspectiveDistortion(max_distortion=0.05)
        img_dist = distortion(image)
        self.assertEqual(img_dist.shape, image.shape)
        
        occlusion = OcclusionSimulation(max_occlusions=1)
        img_occ = occlusion(image)
        self.assertEqual(img_occ.shape, image.shape)
        
        # Test sequence augmentor
        augmentor = VideoStyleAugmentor()
        img_aug = augmentor.augment(image)
        self.assertEqual(img_aug.shape, image.shape)

    def test_track_smoother(self):
        smoother = StreamTrackSmoother(stream_id="test_stream")
        
        # Frame 1: Suspect detected (CID 2, Track ID not assigned yet, confidence 0.9)
        # Box: [100, 100, 200, 200]
        detections_f1 = sv.Detections(
            xyxy=np.array([[100, 100, 200, 200]], dtype=np.float32),
            confidence=np.array([0.9], dtype=np.float32),
            class_id=np.array([2], dtype=np.int32)
        )
        
        # Run track update
        tracks_f1 = smoother.update_with_detections(detections_f1)
        # Bbox should appear immediately (length 1)
        self.assertEqual(len(tracks_f1), 1)
        self.assertEqual(tracks_f1[0]["bbox"], [100, 100, 200, 200])
        
        # Frame 2: Same suspect detected
        detections_f2 = sv.Detections(
            xyxy=np.array([[102, 98, 202, 201]], dtype=np.float32),
            confidence=np.array([0.92], dtype=np.float32),
            class_id=np.array([2], dtype=np.int32)
        )
        tracks_f2 = smoother.update_with_detections(detections_f2)
        self.assertEqual(len(tracks_f2), 1)
        self.assertEqual(tracks_f2[0]["bbox"], [102, 98, 202, 201])
        
        # Frame 3: Same suspect detected
        detections_f3 = sv.Detections(
            xyxy=np.array([[101, 102, 199, 198]], dtype=np.float32),
            confidence=np.array([0.88], dtype=np.float32),
            class_id=np.array([2], dtype=np.int32)
        )
        tracks_f3 = smoother.update_with_detections(detections_f3)
        self.assertEqual(len(tracks_f3), 1)
        
        track = tracks_f3[0]
        self.assertIsNotNone(track["track_id"])
        # Bbox should be the latest raw coordinates for responsiveness
        self.assertEqual(track["bbox"], [101, 102, 199, 198])
        self.assertAlmostEqual(track["confidence"], 0.88, delta=0.01)
        
        # Frame 4: Suspect missed (ghost tracking / survival)
        tracks_f4 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f4), 1)  # Kept alive for 1 frame
        self.assertEqual(tracks_f4[0]["missed_frames"], 1)
        self.assertTrue(tracks_f4[0]["confidence"] < 0.88)  # Confidence decayed

    def test_temporal_feature_extractor(self):
        extractor = TemporalFeatureExtractor(window_size=30)
        
        # Suspect (CID 2, TID 1)
        active_tracks = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9}
        ]
        
        sequences = extractor.update_and_extract(active_tracks, frame_shape=(480, 640))
        self.assertIn(1, sequences)
        seq = sequences[1]
        # Check shape: (30, 12)
        self.assertEqual(seq.shape, (30, 12))
        # First entry and last entry should be similar (due to padding)
        self.assertAlmostEqual(seq[0][0], 100 / 640, delta=0.01)
        self.assertAlmostEqual(seq[-1][0], 100 / 640, delta=0.01)
        self.assertAlmostEqual(seq[-1][8], 0.9, delta=0.01)

    def test_early_exit_logic(self):
        # 1. No weapons and only 1 suspect
        tracked_1 = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9}
        ]
        self.assertFalse(_should_trigger_action_recognition(tracked_1, (480, 640)))
        
        # 2. Weapon detected
        tracked_2 = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            {"track_id": 2, "class_id": 0, "bbox": [150, 150, 170, 170], "confidence": 0.8} # Gun
        ]
        self.assertTrue(_should_trigger_action_recognition(tracked_2, (480, 640)))
        
        # 3. Two suspects far apart
        tracked_3 = [
            {"track_id": 1, "class_id": 2, "bbox": [10, 10, 50, 50], "confidence": 0.9},
            {"track_id": 2, "class_id": 2, "bbox": [500, 400, 550, 450], "confidence": 0.9}
        ]
        self.assertFalse(_should_trigger_action_recognition(tracked_3, (480, 640)))
        
        # 4. Two suspects in close proximity (intersecting bboxes)
        tracked_4 = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            {"track_id": 2, "class_id": 2, "bbox": [150, 150, 250, 250], "confidence": 0.9}
        ]
        self.assertTrue(_should_trigger_action_recognition(tracked_4, (480, 640)))

    def test_numpy_gru_classifier(self):
        classifier = NumPyGRUClassifier(input_dim=12, hidden_dim=32, num_classes=4)
        dummy_seq = np.random.normal(0, 0.1, (30, 12)).astype(np.float32)
        
        idx, score = classifier.predict(dummy_seq)
        self.assertTrue(0 <= idx < 4)
        self.assertTrue(0.0 <= score <= 1.0)


if __name__ == "__main__":
    unittest.main()
