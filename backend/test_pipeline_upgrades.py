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
from bl.detection.temporal_action import TemporalFeatureExtractor, NumPyCNNClassifier
from bl.detection.pipeline import _should_trigger_action_recognition, _merge_detections
from bl.detection.yolo import Detection


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
        # With EMA smoothing (alpha=0.6), bbox is a blend of current and previous.
        # The exact values depend on rounding, but they should be close to the current detection.
        bbox_f2 = tracks_f2[0]["bbox"]
        self.assertTrue(100 <= bbox_f2[0] <= 102, f"x1 {bbox_f2[0]} not in expected range")
        self.assertTrue(98 <= bbox_f2[1] <= 100, f"y1 {bbox_f2[1]} not in expected range")
        
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
        
        # Frame 4: Suspect missed (ghost tracking / survival)
        tracks_f4 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f4), 1)  # Kept alive (suspect ghost frames = 5)
        self.assertEqual(tracks_f4[0]["missed_frames"], 1)
        self.assertTrue(tracks_f4[0]["confidence"] < 0.88)  # Confidence decayed

    def test_ema_smoothing_convergence(self):
        """Verify that EMA-smoothed bbox converges toward the latest detection over multiple frames."""
        smoother = StreamTrackSmoother(stream_id="test_ema")
        
        # Frame 1: initial position
        tracks = smoother.update_with_detections(sv.Detections(
            xyxy=np.array([[100, 100, 200, 200]], dtype=np.float32),
            confidence=np.array([0.9], dtype=np.float32),
            class_id=np.array([2], dtype=np.int32),
        ))
        self.assertEqual(len(tracks), 1)
        
        # Frames 2-10: same detection at a new position — smoothed bbox should converge
        for _ in range(9):
            tracks = smoother.update_with_detections(sv.Detections(
                xyxy=np.array([[150, 150, 250, 250]], dtype=np.float32),
                confidence=np.array([0.9], dtype=np.float32),
                class_id=np.array([2], dtype=np.int32),
            ))
        
        bbox = tracks[0]["bbox"]
        # After 9 updates toward [150,150,250,250], EMA should be very close
        for coord, target in zip(bbox, [150, 150, 250, 250]):
            self.assertAlmostEqual(coord, target, delta=3,
                                   msg=f"EMA coord {coord} should have converged near {target}")

    def test_weapon_ghost_frame_persistence(self):
        """Weapons should survive configured ghost frames instead of being dropped immediately."""
        smoother = StreamTrackSmoother(stream_id="test_weapon_ghost")
        
        # Frame 1: weapon detected (Gun, class_id 0)
        smoother.update_with_detections(sv.Detections(
            xyxy=np.array([[50, 50, 80, 80]], dtype=np.float32),
            confidence=np.array([0.7], dtype=np.float32),
            class_id=np.array([0], dtype=np.int32),
        ))
        
        # Frames 2-3: weapon not detected — should still be alive (ghost frames)
        tracks_f2 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f2), 1, "Weapon should survive 1st ghost frame")
        
        tracks_f3 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f3), 1, "Weapon should survive 2nd ghost frame")
        
        tracks_f4 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f4), 1, "Weapon should survive 3rd ghost frame")
        
        # Frame 5 (4th miss): should be dropped (WEAPON_GHOST_FRAMES=3)
        tracks_f5 = smoother.update_with_detections(sv.Detections.empty())
        self.assertEqual(len(tracks_f5), 0, "Weapon should be dropped after exceeding ghost frames")

    def test_temporal_feature_extractor(self):
        extractor = TemporalFeatureExtractor(window_size=30)
        
        # Suspect (CID 2, TID 1)
        active_tracks = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9}
        ]
        
        sequences = extractor.update_and_extract(active_tracks, frame_shape=(480, 640), frame_seq=1)
        self.assertIn(1, sequences)
        seq = sequences[1]
        # Check shape: (30, 12)
        self.assertEqual(seq.shape, (30, 12))
        # First entry and last entry should be similar (due to padding)
        self.assertAlmostEqual(seq[0][0], 100 / 640, delta=0.01)
        self.assertAlmostEqual(seq[-1][0], 100 / 640, delta=0.01)
        self.assertAlmostEqual(seq[-1][8], 0.9, delta=0.01)

    def test_temporal_historical_weapon_proximity(self):
        """Verify that weapon proximity features use historical per-frame weapon positions,
        not just the current frame's weapons."""
        extractor = TemporalFeatureExtractor(window_size=5)
        
        # Frame 1: Suspect and weapon both present
        tracks_f1 = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            {"track_id": 2, "class_id": 0, "bbox": [120, 120, 160, 160], "confidence": 0.8},  # Gun overlapping
        ]
        extractor.update_and_extract(tracks_f1, (480, 640), frame_seq=1)
        
        # Frame 2: Suspect still present, weapon gone
        tracks_f2 = [
            {"track_id": 1, "class_id": 2, "bbox": [101, 101, 201, 201], "confidence": 0.9},
        ]
        sequences = extractor.update_and_extract(tracks_f2, (480, 640), frame_seq=2)
        
        self.assertIn(1, sequences)
        seq = sequences[1]
        
        # Feature index 9 = min_dist_weapon, index 11 = overlap_weapon.
        # Frame 1's historical entry should still have the weapon proximity data (overlap=1.0)
        # even though frame 2 has no weapon. The left-padded entries before frame 1 should
        # also reflect frame 1's state. The last entry (frame 2) should have no weapon (dist=1.0).
        
        # Last timestep (frame 2): no weapon present
        self.assertAlmostEqual(seq[-1][9], 1.0, delta=0.01, msg="Frame 2 should have no weapon proximity")
        self.assertAlmostEqual(seq[-1][11], 0.0, delta=0.01, msg="Frame 2 should have no weapon overlap")
        
        # Second-to-last timestep (frame 1): weapon was overlapping
        self.assertLess(seq[-2][9], 0.5, msg="Frame 1 should have close weapon proximity")
        self.assertAlmostEqual(seq[-2][11], 1.0, delta=0.01, msg="Frame 1 should have weapon overlap")

    def test_has_weapon_in_window(self):
        """Verify has_weapon_in_window() returns True when a weapon was seen in the temporal window."""
        extractor = TemporalFeatureExtractor(window_size=5)
        
        # No weapons yet
        self.assertFalse(extractor.has_weapon_in_window())
        
        # Add a frame with a weapon
        tracks = [
            {"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            {"track_id": 2, "class_id": 0, "bbox": [120, 120, 160, 160], "confidence": 0.7},
        ]
        extractor.update_and_extract(tracks, (480, 640), frame_seq=1)
        self.assertTrue(extractor.has_weapon_in_window())
        
        # Fill window with no-weapon frames to push weapon entry out
        for i in range(6):
            extractor.update_and_extract(
                [{"track_id": 1, "class_id": 2, "bbox": [100, 100, 200, 200], "confidence": 0.9}],
                (480, 640),
                frame_seq=i + 2,
            )
        # Weapon entry should have been pushed out (window_size=5, we added 6 frames after)
        self.assertFalse(extractor.has_weapon_in_window())

    def test_early_exit_logic(self):
        # 1. No weapons and only 1 suspect
        tracked_1 = [
            Detection(xyxy=(100, 100, 200, 200), score=0.9, label="Suspect", class_id=2)
        ]
        self.assertFalse(_should_trigger_action_recognition(tracked_1, (480, 640)))
        
        # 2. Weapon detected
        tracked_2 = [
            Detection(xyxy=(100, 100, 200, 200), score=0.9, label="Suspect", class_id=2),
            Detection(xyxy=(150, 150, 170, 170), score=0.8, label="Gun", class_id=0),
        ]
        self.assertTrue(_should_trigger_action_recognition(tracked_2, (480, 640)))
        
        # 3. Two suspects far apart
        tracked_3 = [
            Detection(xyxy=(10, 10, 50, 50), score=0.9, label="Suspect", class_id=2),
            Detection(xyxy=(500, 400, 550, 450), score=0.9, label="Suspect", class_id=2),
        ]
        self.assertFalse(_should_trigger_action_recognition(tracked_3, (480, 640)))
        
        # 4. Two suspects in close proximity (intersecting bboxes)
        tracked_4 = [
            Detection(xyxy=(100, 100, 200, 200), score=0.9, label="Suspect", class_id=2),
            Detection(xyxy=(150, 150, 250, 250), score=0.9, label="Suspect", class_id=2),
        ]
        self.assertTrue(_should_trigger_action_recognition(tracked_4, (480, 640)))

    def test_merge_detections_with_cross_model_nms(self):
        """Verify that _merge_detections de-duplicates suspect boxes from both models via NMS."""
        # Weapon model: a Gun (kept) and a Suspect (kept, will be NMS'd against person model)
        weapon_detections = [
            Detection(xyxy=(10, 10, 20, 20), score=0.9, label="Gun", class_id=0),
            Detection(xyxy=(50, 50, 150, 150), score=0.5, label="Suspect", class_id=2),
        ]
        # Person model (COCO ids): overlapping person box (should be NMS-deduplicated)
        person_detections = [
            Detection(xyxy=(55, 55, 145, 145), score=0.8, label="person", class_id=0),  # overlaps with weapon model's suspect
        ]

        merged = _merge_detections(weapon_detections, person_detections, suspect_label="Suspect")

        # Should have 1 Gun + 1 Suspect (de-duplicated), not 1 Gun + 2 Suspects
        self.assertEqual(len(merged), 2, f"Expected 2 detections (1 gun + 1 suspect), got {len(merged)}")
        guns = [d for d in merged if d.class_id == 0]
        suspects = [d for d in merged if d.class_id == 2]
        self.assertEqual(len(guns), 1)
        self.assertEqual(len(suspects), 1)
        # NMS should keep the higher-scoring suspect (the person model's 0.8)
        self.assertAlmostEqual(suspects[0].score, 0.8, delta=0.01)

    def test_merge_detections_non_overlapping(self):
        """When suspect boxes don't overlap, both should be kept."""
        weapon_detections = [
            Detection(xyxy=(10, 10, 20, 20), score=0.9, label="Gun", class_id=0),
            Detection(xyxy=(30, 30, 40, 40), score=0.5, label="Suspect", class_id=2),
        ]
        person_detections = [
            Detection(xyxy=(300, 300, 400, 400), score=0.8, label="person", class_id=0),
        ]

        merged = _merge_detections(weapon_detections, person_detections, suspect_label="Suspect")

        self.assertEqual(len(merged), 3, "Non-overlapping suspects should both be kept")
        guns = [d for d in merged if d.class_id == 0]
        suspects = [d for d in merged if d.class_id == 2]
        self.assertEqual(len(guns), 1)
        self.assertEqual(len(suspects), 2)

    def test_numpy_cnn_classifier(self):
        classifier = NumPyCNNClassifier(input_dim=12, hidden_channels=32, num_classes=3)
        dummy_seq = np.random.normal(0, 0.1, (30, 12)).astype(np.float32)

        idx, score = classifier.predict(dummy_seq)
        self.assertTrue(0 <= idx < 3)
        self.assertTrue(0.0 <= score <= 1.0)


if __name__ == "__main__":
    unittest.main()
