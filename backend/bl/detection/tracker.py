from __future__ import annotations

import threading

import supervision as sv

_tracker_lock = threading.Lock()
_byte_trackers: dict[str, sv.ByteTrack] = {}

_frame_seq_lock = threading.Lock()
_frame_seq: dict[str, int] = {}


def get_byte_tracker(stream_id: str) -> sv.ByteTrack:
    with _tracker_lock:
        if stream_id not in _byte_trackers:
            _byte_trackers[stream_id] = sv.ByteTrack()
        return _byte_trackers[stream_id]


def remove_byte_tracker(stream_id: str) -> None:
    with _tracker_lock:
        _byte_trackers.pop(stream_id, None)


def next_frame_seq(stream_id: str) -> int:
    with _frame_seq_lock:
        n = _frame_seq.get(stream_id, 0) + 1
        _frame_seq[stream_id] = n
        return n
