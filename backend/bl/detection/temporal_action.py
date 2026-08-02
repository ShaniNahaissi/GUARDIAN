from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any
import numpy as np

logger = logging.getLogger("guardian.temporal_action")

# Classes recognized by the temporal model. Stabbing was dropped from this taxonomy: the
# real-data training source (UCF-Crime, see temporal_training/) has no matching category and
# no other real data source is planned for it, so it would only ever ship untrained.
ACTION_CLASSES = {
    0: "Normal",
    1: "Shooting",
    2: "Violence"
}

class TemporalFeatureExtractor:
    """Compiles track histories and computes multi-frame feature vectors for action recognition.
    
    Key fix: weapon bounding boxes are now stored per-frame in the history so that weapon-proximity
    features (min_dist_weapon, overlap_weapon) reflect the actual weapon positions at each historical
    timestep, not just the current frame's weapons projected across the entire window."""
    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        # Dictionary mapping track_id -> list of raw track states: (bbox [x1, y1, x2, y2], confidence, timestamp)
        self.history: dict[int, list[dict[str, Any]]] = {}
        # Last frame_seq at which each track was seen. Used to expire history entries
        # only after a track has been absent for > window_size frames, rather than
        # pruning eagerly on the very first frame a track is missing. Eager pruning
        # caused the temporal classifier to lose a threat's action sequence mid-event
        # when the track briefly exited ByteTrack's output (e.g. during ghost frames),
        # resetting it to Normal before re-acquiring the same track.
        self._last_seen: dict[int, int] = {}
        # Per-frame weapon positions, keyed by frame_seq so that historical feature extraction
        # can look up where weapons were at each past timestep instead of using only the current
        # frame's weapons for all 30 steps (which was the root cause of broken proximity features).
        self._weapon_history: list[dict[str, Any]] = []

    def has_weapon_in_window(self) -> bool:
        """Returns True if any weapon was detected within the recent temporal window.
        Used by the pipeline to make the static-displacement filter weapon-aware —
        a stationary person near a weapon should NOT be short-circuited to Normal."""
        return len(self._weapon_history) > 0

    def update_and_extract(
        self,
        active_tracks: list[dict[str, Any]],
        frame_shape: tuple[int, int],
        frame_seq: int
    ) -> dict[int, np.ndarray]:
        """Updates track history, calculates velocities & proximity features, and returns feature sequences."""
        h, w = frame_shape
        tids = {t["track_id"] for t in active_tracks}

        # Expire tracks that have not been seen for more than window_size frames.
        # Using window_size (not 1) as the threshold prevents premature history pruning:
        # the smoother emits ghost tracks for a few frames after the object leaves the
        # frame, but those ghost frames may not always reach the extractor in lock-step.
        # Allowing window_size frames of absence before pruning means the classifier
        # never loses a threat's action sequence mid-event due to a transient absence.
        current_seq = frame_seq
        dead_ids = [
            tid for tid, last in self._last_seen.items()
            if tid not in tids and (current_seq - last) > self.window_size
        ]
        for tid in dead_ids:
            self.history.pop(tid, None)
            self._last_seen.pop(tid, None)

        # Update histories for active tracks
        for t in active_tracks:
            tid = t["track_id"]
            self._last_seen[tid] = frame_seq
            self.history.setdefault(tid, []).append({
                "bbox": t["bbox"],
                "class_id": t["class_id"],
                "confidence": t["confidence"],
                "frame_seq": frame_seq
            })
            if len(self.history[tid]) > self.window_size:
                self.history[tid].pop(0)

        # Store this frame's weapon positions in the per-frame weapon history.
        weapon_tracks_this_frame = [t for t in active_tracks if t["class_id"] in (0, 1)]
        weapon_entry = {
            "frame_seq": frame_seq,
            "weapons": [{"bbox": t["bbox"], "class_id": t["class_id"]} for t in weapon_tracks_this_frame],
        }
        self._weapon_history.append(weapon_entry)
        if len(self._weapon_history) > self.window_size:
            self._weapon_history.pop(0)

        # Build a lookup from frame_seq -> list of weapon bboxes for efficient historical access.
        weapon_by_frame: dict[int, list[dict[str, Any]]] = {}
        for entry in self._weapon_history:
            weapon_by_frame[entry["frame_seq"]] = entry["weapons"]

        # Extract features for each Suspect track (class_id = 2 is Suspect in names.txt)
        sequences: dict[int, np.ndarray] = {}
        
        # Separate suspects for inter-suspect proximity (current frame).
        suspect_tracks = [t for t in active_tracks if t["class_id"] == 2]

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
                
                # 4. Proximity to weapons — now uses HISTORICAL per-frame weapon positions
                #    instead of projecting the current frame's weapons across the entire window.
                min_dist_weapon = 1.0
                overlap_weapon = 0.0
                
                hist_frame_seq = state["frame_seq"]
                hist_weapons = weapon_by_frame.get(hist_frame_seq, [])
                
                s_cx, s_cy = (x1 + x2) / 2, (y1 + y2) / 2
                for weapon in hist_weapons:
                    wx1, wy1, wx2, wy2 = weapon["bbox"]
                    w_cx, w_cy = (wx1 + wx2) / 2, (wy1 + wy2) / 2
                    
                    # Center distance normalized by frame dimensions
                    dist = (((s_cx - w_cx) / w) ** 2 + ((s_cy - w_cy) / h) ** 2) ** 0.5
                    min_dist_weapon = min(min_dist_weapon, dist)
                    
                    # Check box overlap
                    ix1 = max(x1, wx1)
                    iy1 = max(y1, wy1)
                    ix2 = min(x2, wx2)
                    iy2 = min(y2, wy2)
                    if ix2 > ix1 and iy2 > iy1:
                        overlap_weapon = 1.0

                # 5. Proximity to other suspects (current frame only, same as before)
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


KERNEL_SIZE = 5  # must match temporal_training/model.py's TemporalCNNClassifier


def conv1d_same(x: np.ndarray, w: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Same-padding 1D convolution, stride 1. x: (in_ch, seq_len), w: (out_ch, in_ch, kernel),
    b: (out_ch,) -> (out_ch, seq_len)."""
    out_ch, in_ch, kernel = w.shape
    pad = kernel // 2
    seq_len = x.shape[1]
    x_padded = np.pad(x, ((0, 0), (pad, pad)))
    out = np.empty((out_ch, seq_len), dtype=np.float32)
    for t in range(seq_len):
        window = x_padded[:, t:t + kernel]  # (in_ch, kernel)
        out[:, t] = np.tensordot(w, window, axes=([1, 2], [0, 1])) + b
    return out


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


class NumPyCNNClassifier:
    """NumPy-based inference implementation of the 1D-CNN temporal action classifier: two
    same-padded conv1d layers over the time axis, global-average-pooled, then a linear head.
    Trained via temporal_training/temporal_training.ipynb (see that folder's
    TemporalCNNClassifier/export_to_numpy_weights_cnn for the matching PyTorch training model
    and exporter -- same conv1_w/conv1_b/conv2_w/conv2_b/fc_w/fc_b weight contract)."""
    def __init__(self, input_dim: int = 12, hidden_channels: int = 32, num_classes: int = 3) -> None:
        self.input_dim = input_dim
        self.hidden_channels = hidden_channels
        self.num_classes = num_classes

        # Untrained (random) weights would silently make threat detection non-functional --
        # fail loudly at startup instead of shipping a classifier that can never really alert.
        weights_path = Path(__file__).resolve().parents[3] / "trained_model" / "temporal_action_weights.npz"
        if not weights_path.exists():
            raise FileNotFoundError(
                f"Temporal action weights not found at {weights_path}. "
                "Run temporal_training/temporal_training.ipynb to produce them."
            )

        data = np.load(weights_path)
        self.conv1_w = data["conv1_w"]
        self.conv1_b = data["conv1_b"]
        self.conv2_w = data["conv2_w"]
        self.conv2_b = data["conv2_b"]
        self.fc_w = data["fc_w"]
        self.fc_b = data["fc_b"]
        logger.info("Loaded temporal action weights from %s", weights_path)

    def forward(self, seq: np.ndarray) -> np.ndarray:
        """Runs the sequence through the conv stack and linear layer. seq shape: (seq_len, input_dim)"""
        x = np.ascontiguousarray(seq.T, dtype=np.float32)  # (input_dim, seq_len)
        x = _relu(conv1d_same(x, self.conv1_w, self.conv1_b))
        x = _relu(conv1d_same(x, self.conv2_w, self.conv2_b))
        pooled = x.mean(axis=1)  # (hidden_channels,)
        logits = self.fc_w @ pooled + self.fc_b
        exp_logits = np.exp(logits - np.max(logits))  # stable softmax
        return exp_logits / np.sum(exp_logits)

    def predict(self, seq: np.ndarray) -> tuple[int, float]:
        """Returns the index of the predicted action and its confidence score."""
        probs = self.forward(seq)
        cls_idx = int(np.argmax(probs))
        return cls_idx, float(probs[cls_idx])
