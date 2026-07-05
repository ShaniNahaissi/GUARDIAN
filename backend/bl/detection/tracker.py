from __future__ import annotations

import threading
import logging
from typing import Any
import numpy as np
import supervision as sv

logger = logging.getLogger("guardian.tracker")

class TrackState:
    """Manages the state history of a single tracked object for temporal smoothing."""
    def __init__(self, track_id: int, class_id: int, bbox: list[int], score: float) -> None:
        self.track_id = track_id
        self.class_id = class_id
        self.bbox_history: list[list[int]] = [bbox]
        self.score_history: list[float] = [score]
        self.missed_frames = 0
        self.total_detections = 1
        self.is_validated = False

    def update(self, bbox: list[int], score: float) -> None:
        self.bbox_history.append(bbox)
        if len(self.bbox_history) > 5:
            self.bbox_history.pop(0)
        self.score_history.append(score)
        if len(self.score_history) > 5:
            self.score_history.pop(0)
        self.missed_frames = 0
        self.total_detections += 1
        # False Positive reduction: validate track if seen in at least 3 frames
        if self.total_detections >= 3:
            self.is_validated = True

    def get_smoothed_bbox(self) -> list[int]:
        """Averages the bounding box coordinates over the history window."""
        arr = np.array(self.bbox_history)
        mean_box = np.mean(arr, axis=0).astype(int).tolist()
        return mean_box

    def get_smoothed_score(self) -> float:
        """Averages the confidence score over the history window."""
        return float(np.mean(self.score_history))


class StreamTrackSmoother:
    """Wraps ByteTrack and applies bounding box smoothing, flicker recovery, and track validation."""
    def __init__(self, stream_id: str) -> None:
        self.stream_id = stream_id
        self.tracker = sv.ByteTrack()
        self.active_tracks: dict[int, TrackState] = {}
        # Keep track of class names or configurations
        self.lock = threading.Lock()

    def update_with_detections(self, detections: sv.Detections) -> list[dict[str, Any]]:
        with self.lock:
            # Run ByteTrack update
            tracked = self.tracker.update_with_detections(detections)
            
            seen_tids = set()
            
            if tracked.xyxy is not None and len(tracked.xyxy) > 0:
                tids = tracked.tracker_id
                confs = tracked.confidence
                classes = tracked.class_id
                for i in range(len(tracked.xyxy)):
                    x1, y1, x2, y2 = map(int, tracked.xyxy[i].tolist())
                    tid = int(tids[i]) if tids is not None else -1
                    score = float(confs[i]) if confs is not None else 1.0
                    cid = int(classes[i]) if classes is not None else 0
                    
                    if tid == -1:
                        continue
                        
                    seen_tids.add(tid)
                    
                    if tid in self.active_tracks:
                        self.active_tracks[tid].update([x1, y1, x2, y2], score)
                    else:
                        self.active_tracks[tid] = TrackState(tid, cid, [x1, y1, x2, y2], score)
            
            # Handle missed tracks (flicker recovery / ghost tracks)
            dead_tids = []
            for tid, state in self.active_tracks.items():
                if tid not in seen_tids:
                    state.missed_frames += 1
                    if state.missed_frames <= 3:  # Allow track to survive 3 frames without detection
                        # Decay confidence score slightly per missed frame
                        decayed_score = state.get_smoothed_score() * 0.8
                        state.score_history.append(decayed_score)
                        if len(state.score_history) > 5:
                            state.score_history.pop(0)
                    else:
                        dead_tids.append(tid)
                        
            for tid in dead_tids:
                self.active_tracks.pop(tid, None)
                
            # Compile outputs (only validated tracks to minimize transient false positives)
            smoothed_tracks = []
            for tid, state in self.active_tracks.items():
                if state.is_validated or state.total_detections >= 3:
                    smoothed_tracks.append({
                        "track_id": tid,
                        "bbox": state.get_smoothed_bbox(),
                        "class_id": state.class_id,
                        "confidence": state.get_smoothed_score(),
                        "missed_frames": state.missed_frames,
                    })
            return smoothed_tracks


_tracker_lock = threading.Lock()
_byte_trackers: dict[str, StreamTrackSmoother] = {}

_frame_seq_lock = threading.Lock()
_frame_seq: dict[str, int] = {}


def get_byte_tracker(stream_id: str) -> StreamTrackSmoother:
    with _tracker_lock:
        if stream_id not in _byte_trackers:
            _byte_trackers[stream_id] = StreamTrackSmoother(stream_id)
        return _byte_trackers[stream_id]


def remove_byte_tracker(stream_id: str) -> None:
    with _tracker_lock:
        _byte_trackers.pop(stream_id, None)


def next_frame_seq(stream_id: str) -> int:
    with _frame_seq_lock:
        n = _frame_seq.get(stream_id, 0) + 1
        _frame_seq[stream_id] = n
        return n
