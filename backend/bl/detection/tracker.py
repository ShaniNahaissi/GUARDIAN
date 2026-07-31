from __future__ import annotations

import threading
import logging
from typing import Any
import numpy as np
import supervision as sv

from bl.detection.config import WEAPON_CONF_THRESHOLD

logger = logging.getLogger("guardian.tracker")

class TrackState:
    """Manages the state history of a single tracked object for temporal features and responsiveness."""
    def __init__(self, track_id: int, class_id: int, bbox: list[int], score: float) -> None:
        self.track_id = track_id
        self.class_id = class_id
        self.bbox_history: list[list[int]] = [bbox]
        self.score_history: list[float] = [score]
        self.missed_frames = 0
        self.total_detections = 1
        self.latest_bbox = bbox

    def update(self, bbox: list[int], score: float) -> None:
        self.latest_bbox = bbox
        self.bbox_history.append(bbox)
        if len(self.bbox_history) > 35:  # Keep window history for action recognition
            self.bbox_history.pop(0)
        self.score_history.append(score)
        if len(self.score_history) > 35:
            self.score_history.pop(0)
        self.missed_frames = 0
        self.total_detections += 1

    def get_latest_bbox(self) -> list[int]:
        """Returns the raw latest bounding box for maximum responsiveness and zero coordinate lag."""
        return self.latest_bbox

    def get_latest_score(self) -> float:
        """Returns the latest confidence score."""
        return self.score_history[-1] if self.score_history else 0.0


class StreamTrackSmoother:
    """Wraps ByteTrack and applies responsive state management, instant detection display, and class smoothing."""
    def __init__(self, stream_id: str) -> None:
        self.stream_id = stream_id
        # ByteTrack internally requires det_thresh = track_activation_threshold + 0.1 to CREATE a
        # brand-new track (see supervision's byte_tracker/core.py) -- a detection scoring between
        # track_activation_threshold and that +0.1 bump can only continue an existing track, never
        # start one. Passing WEAPON_CONF_THRESHOLD directly here left a 0.1-wide dead zone where
        # nothing could ever get a first id. Subtracting 0.1 lines det_thresh back up with the
        # detector's own floor, so anything we actually let through can start a track.
        # minimum_matching_threshold lowered from its 0.8 default: that's the IoU required between
        # frames to keep the same track id, too strict for small/fast-moving objects like a gun.
        # lost_track_buffer raised from 30: how many frames a track survives with no matching
        # detection before it's dropped -- higher lets sparse/intermittent weapon detections still
        # bridge back to the same id instead of dying and needing to re-clear det_thresh again.
        self.tracker = sv.ByteTrack(
            track_activation_threshold=max(0.0, WEAPON_CONF_THRESHOLD - 0.1),
            minimum_matching_threshold=0.3,
            lost_track_buffer=60,
        )
        self.active_tracks: dict[int, TrackState] = {}
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
                    # Suspects (class 2) survive 1 frame, weapons (class 0, 1) survive 0 frames to prevent ghosting
                    max_missed = 1 if state.class_id == 2 else 0
                    if state.missed_frames <= max_missed:
                        # Decay confidence score per missed frame
                        decayed_score = state.get_latest_score() * 0.7
                        state.score_history.append(decayed_score)
                    else:
                        dead_tids.append(tid)
                        
            for tid in dead_tids:
                self.active_tracks.pop(tid, None)
                
            # Compile outputs
            tracks_out = []
            for tid, state in self.active_tracks.items():
                # Detections appear immediately (total_detections >= 1) to eliminate latency in UI box display
                tracks_out.append({
                    "track_id": tid,
                    "bbox": state.get_latest_bbox(),
                    "class_id": state.class_id,
                    "confidence": state.get_latest_score(),
                    "missed_frames": state.missed_frames,
                })
            return tracks_out


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
