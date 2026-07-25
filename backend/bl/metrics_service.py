from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select

from dal.database import SessionLocal
from models.metrics import FrameMetric, SequenceMetric

logger = logging.getLogger("guardian.metrics_service")


async def save_metrics_to_db(
    stream_id: str,
    frame_seq: int,
    total_latency_ms: float,
    yolo_latency_ms: float,
    detections_count: int,
    track_count: int,
    detections_json: list[dict[str, Any]],
    cpu_utilization: float,
    gpu_vram_used: int,
    evaluated_sequences: list[dict[str, Any]],
    person_latency_ms: float = 0.0,
    action_latency_ms: float = 0.0,
) -> None:
    """Saves frame-level metrics and any evaluated sequences to the database asynchronously."""
    try:
        async with SessionLocal() as session:
            # 1. Create and add FrameMetric
            frame_metric = FrameMetric(
                stream_id=stream_id,
                frame_seq=frame_seq,
                total_latency_ms=total_latency_ms,
                yolo_latency_ms=yolo_latency_ms,
                person_latency_ms=person_latency_ms,
                action_latency_ms=action_latency_ms,
                detections_count=detections_count,
                track_count=track_count,
                detections_json=detections_json,
                cpu_utilization=cpu_utilization,
                gpu_vram_used=gpu_vram_used,
            )
            session.add(frame_metric)

            # Flush to database so these values are available for aggregate queries if needed
            await session.flush()

            # 2. Save SequenceMetric entries
            for seq_data in evaluated_sequences:
                # Query average latency per model over the frame sequence window
                stmt = select(
                    func.avg(FrameMetric.total_latency_ms),
                    func.avg(FrameMetric.yolo_latency_ms),
                    func.avg(FrameMetric.person_latency_ms),
                    func.avg(FrameMetric.action_latency_ms),
                ).where(
                    FrameMetric.stream_id == stream_id,
                    FrameMetric.frame_seq >= seq_data["start_frame_seq"],
                    FrameMetric.frame_seq <= seq_data["end_frame_seq"],
                )
                res = await session.execute(stmt)
                row = res.fetchone()
                avg_total, avg_yolo, avg_person, avg_action = row if row else (None, None, None, None)

                # Check for None values (if no records found, fallback to current frame metrics)
                avg_total = float(avg_total) if avg_total is not None else total_latency_ms
                avg_yolo = float(avg_yolo) if avg_yolo is not None else yolo_latency_ms
                avg_person = float(avg_person) if avg_person is not None else person_latency_ms
                avg_action = float(avg_action) if avg_action is not None else action_latency_ms

                seq_metric = SequenceMetric(
                    stream_id=stream_id,
                    track_id=seq_data["track_id"],
                    start_frame_seq=seq_data["start_frame_seq"],
                    end_frame_seq=seq_data["end_frame_seq"],
                    action_label=seq_data["action_label"],
                    action_confidence=seq_data["action_confidence"],
                    best_frame_seq=seq_data["best_frame_seq"],
                    best_frame_score=seq_data["best_frame_score"],
                    avg_total_latency_ms=avg_total,
                    avg_yolo_latency_ms=avg_yolo,
                    avg_person_latency_ms=avg_person,
                    avg_action_latency_ms=avg_action,
                    frame_count=max(1, seq_data["end_frame_seq"] - seq_data["start_frame_seq"] + 1),
                )
                session.add(seq_metric)

            await session.commit()
    except Exception as e:
        logger.error("Failed to save metrics to database: %s", e, exc_info=True)
