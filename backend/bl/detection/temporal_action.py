from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any
import numpy as np

logger = logging.getLogger("guardian.temporal_action")

# Classes recognized by the temporal model
ACTION_CLASSES = {
    0: "Normal",
    1: "Shooting",
    2: "Stabbing",
    3: "Violence"
}

class TemporalFeatureExtractor:
    """Compiles track histories and computes multi-frame feature vectors for action recognition."""
    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        # Dictionary mapping track_id -> list of raw track states: (bbox [x1, y1, x2, y2], confidence, timestamp)
        self.history: dict[int, list[dict[str, Any]]] = {}

    def update_and_extract(
        self,
        active_tracks: list[dict[str, Any]],
        frame_shape: tuple[int, int]
    ) -> dict[int, np.ndarray]:
        """Updates track history, calculates velocities & proximity features, and returns feature sequences."""
        h, w = frame_shape
        tids = {t["track_id"] for t in active_tracks}
        
        # Prune dead tracks from history
        dead_ids = [tid for tid in self.history if tid not in tids]
        for tid in dead_ids:
            self.history.pop(tid, None)
            
        # Update histories for active tracks
        for t in active_tracks:
            tid = t["track_id"]
            self.history.setdefault(tid, []).append({
                "bbox": t["bbox"],
                "class_id": t["class_id"],
                "confidence": t["confidence"]
            })
            if len(self.history[tid]) > self.window_size:
                self.history[tid].pop(0)

        # Extract features for each Suspect track (class_id = 2 is Suspect in names.txt)
        sequences: dict[int, np.ndarray] = {}
        
        # Separate weapons and suspects
        weapon_tracks = [t for t in active_tracks if t["class_id"] in (0, 1)] # 0: Gun, 1: Knife
        suspect_tracks = [t for t in active_tracks if t["class_id"] == 2] # 2: Suspect

        for suspect in suspect_tracks:
            tid = suspect["track_id"]
            track_hist = self.history.get(tid, [])
            if not track_hist:
                continue
                
            seq_features = []
            
            # Walk history up to window_size (pad by repeating first state if history is short)
            hist_len = len(track_hist)
            for idx in range(self.window_size):
                # If history is shorter than window, repeat first state for left-padding
                hist_idx = max(0, idx - (self.window_size - hist_len))
                state = track_hist[hist_idx]
                
                # 1. Normalize current bbox coordinates [0, 1]
                x1, y1, x2, y2 = state["bbox"]
                nx1, ny1, nx2, ny2 = x1 / w, y1 / h, x2 / w, y2 / h
                
                # 2. Bbox Velocities (dx, dy)
                if hist_idx > 0:
                    prev_state = track_hist[hist_idx - 1]
                    px1, py1, px2, py2 = prev_state["bbox"]
                    dx1 = (x1 - px1) / w
                    dy1 = (y1 - py1) / h
                    dx2 = (x2 - px2) / w
                    dy2 = (y2 - py2) / h
                else:
                    dx1 = dy1 = dx2 = dy2 = 0.0
                    
                # 3. Detection Confidence
                conf = state["confidence"]
                
                # 4. Proximity to weapons (relative distance and overlap)
                min_dist_weapon = 1.0
                overlap_weapon = 0.0
                
                # Find closest active weapon in this historical frame
                # Since we don't have full history for other tracks in past frames, we approximate
                # proximity using the current frame's active weapon tracks
                s_cx, s_cy = (x1 + x2) / 2, (y1 + y2) / 2
                for weapon in weapon_tracks:
                    wx1, wy1, wx2, wy2 = weapon["bbox"]
                    w_cx, w_cy = (wx1 + wx2) / 2, (wy1 + wy2) / 2
                    
                    # Center distance normalized by frame width
                    dist = (((s_cx - w_cx) / w) ** 2 + ((s_cy - w_cy) / h) ** 2) ** 0.5
                    min_dist_weapon = min(min_dist_weapon, dist)
                    
                    # Check box overlap
                    ix1 = max(x1, wx1)
                    iy1 = max(y1, wy1)
                    ix2 = min(x2, wx2)
                    iy2 = min(y2, wy2)
                    if ix2 > ix1 and iy2 > iy1:
                        overlap_weapon = 1.0

                # 5. Proximity to other suspects
                min_dist_suspect = 1.0
                for other in suspect_tracks:
                    if other["track_id"] == tid:
                        continue
                    ox1, oy1, ox2, oy2 = other["bbox"]
                    o_cx, o_cy = (ox1 + ox2) / 2, (oy1 + oy2) / 2
                    dist = (((s_cx - o_cx) / w) ** 2 + ((s_cy - o_cy) / h) ** 2) ** 0.5
                    min_dist_suspect = min(min_dist_suspect, dist)
                    
                # Compile feature vector of size 12
                feat = [
                    nx1, ny1, nx2, ny2,
                    dx1, dy1, dx2, dy2,
                    conf,
                    min_dist_weapon,
                    min_dist_suspect,
                    overlap_weapon
                ]
                seq_features.append(feat)
                
            sequences[tid] = np.array(seq_features, dtype=np.float32)
            
        return sequences


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))


class NumPyGRUClassifier:
    """NumPy-based inference implementation of a lightweight GRU temporal action classifier."""
    def __init__(self, input_dim: int = 12, hidden_dim: int = 32, num_classes: int = 4) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        
        # Load weights or initialize
        self.weights_loaded = False
        weights_path = Path(__file__).resolve().parents[3] / "trained_model" / "temporal_action_weights.npz"
        
        if weights_path.exists():
            try:
                data = np.load(weights_path)
                self.w_ih = data["w_ih"]
                self.w_hh = data["w_hh"]
                self.b_ih = data["b_ih"]
                self.b_hh = data["b_hh"]
                self.w_fc = data["w_fc"]
                self.b_fc = data["b_fc"]
                self.weights_loaded = True
                logger.info("Loaded temporal action weights from %s", weights_path)
            except Exception as e:
                logger.error("Failed to load weights: %s. Re-initializing...", e)
                
        if not self.weights_loaded:
            # Initialize weights deterministically to avoid pure random drift
            rng = np.random.default_rng(42)
            self.w_ih = rng.normal(0, 0.1, (3 * hidden_dim, input_dim)).astype(np.float32)
            self.w_hh = rng.normal(0, 0.1, (3 * hidden_dim, hidden_dim)).astype(np.float32)
            self.b_ih = np.zeros(3 * hidden_dim, dtype=np.float32)
            self.b_hh = np.zeros(3 * hidden_dim, dtype=np.float32)
            
            # Simple linear mapping to output classes
            self.w_fc = rng.normal(0, 0.1, (num_classes, hidden_dim)).astype(np.float32)
            self.b_fc = np.zeros(num_classes, dtype=np.float32)
            logger.warning(
                "Initialized temporal action classifier with default weights (Not Trained). "
                "Run train_temporal_action.py to produce weights."
            )

    def forward(self, seq: np.ndarray) -> np.ndarray:
        """Runs the sequence through the GRU cell and linear layer. seq shape: (seq_len, input_dim)"""
        seq_len, feat_dim = seq.shape
        h = np.zeros(self.hidden_dim, dtype=np.float32)
        
        for t in range(seq_len):
            x = seq[t]
            
            # Pre-compute parts
            gi = np.dot(self.w_ih, x) + self.b_ih
            gh = np.dot(self.w_hh, h) + self.b_hh
            
            # Split into reset, update, and new gates
            # PyTorch GRU layout: r, z, n (reset, update, new)
            i_r, i_z, i_n = np.split(gi, 3)
            h_r, h_z, h_n = np.split(gh, 3)
            
            r = sigmoid(i_r + h_r)
            z = sigmoid(i_z + h_z)
            n = np.tanh(i_n + r * h_n)
            
            h = (1.0 - z) * n + z * h
            
        # Fully connected output
        logits = np.dot(self.w_fc, h) + self.b_fc
        # Softmax to get class probabilities
        exp_logits = np.exp(logits - np.max(logits)) # stable softmax
        probs = exp_logits / np.sum(exp_logits)
        return probs

    def predict(self, seq: np.ndarray) -> tuple[int, float]:
        """Returns the index of the predicted action and its confidence score."""
        probs = self.forward(seq)
        cls_idx = int(np.argmax(probs))
        return cls_idx, float(probs[cls_idx])
