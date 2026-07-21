from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from dal.database import Base


class FrameMetric(Base):
    __tablename__ = "frame_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frame_seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    yolo_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    detections_count: Mapped[int] = mapped_column(Integer, nullable=False)
    track_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detections_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    cpu_utilization: Mapped[float] = mapped_column(Float, nullable=False)
    gpu_vram_used: Mapped[int] = mapped_column(Integer, nullable=False)


class SequenceMetric(Base):
    __tablename__ = "sequence_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_frame_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    action_label: Mapped[str] = mapped_column(String(64), nullable=False)
    action_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    best_frame_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    best_frame_score: Mapped[float] = mapped_column(Float, nullable=False)
    avg_total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    avg_yolo_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False)
