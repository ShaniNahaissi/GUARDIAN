from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bl import admin_user_service
from dal.database import get_session
from dependencies.security import get_admin_user
from models.user import User
from models.metrics import FrameMetric, SequenceMetric
from schemas.admin import AdminCreateUser, AdminUpdateUser, AdminUserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: User = Depends(get_admin_user),
) -> list[AdminUserOut]:
    return await admin_user_service.list_users(session)


@router.post("/users", response_model=AdminUserOut)
async def create_user(
    body: AdminCreateUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: User = Depends(get_admin_user),
) -> AdminUserOut:
    return await admin_user_service.create_user(session, body)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUpdateUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: User = Depends(get_admin_user),
) -> AdminUserOut:
    return await admin_user_service.update_user(session, user_id, body)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: User = Depends(get_admin_user),
) -> dict[str, bool]:
    await admin_user_service.delete_user(session, user_id, admin.id)
    return {"ok": True}


@router.get("/metrics/summary")
async def get_metrics_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: User = Depends(get_admin_user),
) -> dict[str, Any]:
    total_frames = (await session.execute(select(func.count()).select_from(FrameMetric))).scalar_one() or 0
    avg_total_latency = (await session.execute(select(func.avg(FrameMetric.total_latency_ms)))).scalar_one() or 0.0
    avg_yolo_latency = (await session.execute(select(func.avg(FrameMetric.yolo_latency_ms)))).scalar_one() or 0.0
    total_sequences = (await session.execute(select(func.count()).select_from(SequenceMetric))).scalar_one() or 0
    threat_sequences = (await session.execute(select(func.count()).select_from(SequenceMetric).where(SequenceMetric.action_label != "Normal"))).scalar_one() or 0

    return {
        "total_frames_processed": total_frames,
        "avg_total_latency_ms": round(float(avg_total_latency), 2),
        "avg_yolo_latency_ms": round(float(avg_yolo_latency), 2),
        "total_sequences_analyzed": total_sequences,
        "threats_detected_count": threat_sequences,
    }


@router.get("/metrics/frame-series")
async def get_frame_series(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 100,
    _: User = Depends(get_admin_user),
) -> list[dict[str, Any]]:
    stmt = select(
        FrameMetric.timestamp,
        FrameMetric.frame_seq,
        FrameMetric.total_latency_ms,
        FrameMetric.yolo_latency_ms,
        FrameMetric.track_count,
        FrameMetric.detections_count,
        FrameMetric.cpu_utilization,
        FrameMetric.gpu_vram_used,
    ).order_by(FrameMetric.timestamp.desc()).limit(limit)
    
    res = await session.execute(stmt)
    rows = res.fetchall()
    
    out = []
    for r in reversed(rows):
        out.append({
            "timestamp": r[0].isoformat() if r[0] else None,
            "frame_seq": r[1],
            "total_latency_ms": round(float(r[2]), 2),
            "yolo_latency_ms": round(float(r[3]), 2),
            "track_count": r[4],
            "detections_count": r[5],
            "cpu_utilization": round(float(r[6]), 2),
            "gpu_vram_used": r[7],
        })
    return out


@router.get("/metrics/sequences")
async def get_sequences(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
    _: User = Depends(get_admin_user),
) -> list[dict[str, Any]]:
    stmt = select(
        SequenceMetric.timestamp,
        SequenceMetric.stream_id,
        SequenceMetric.track_id,
        SequenceMetric.start_frame_seq,
        SequenceMetric.end_frame_seq,
        SequenceMetric.action_label,
        SequenceMetric.action_confidence,
        SequenceMetric.best_frame_seq,
        SequenceMetric.best_frame_score,
        SequenceMetric.avg_total_latency_ms,
        SequenceMetric.avg_yolo_latency_ms,
        SequenceMetric.frame_count,
    ).order_by(SequenceMetric.timestamp.desc()).limit(limit)
    
    res = await session.execute(stmt)
    rows = res.fetchall()
    
    out = []
    for r in rows:
        out.append({
            "timestamp": r[0].isoformat() if r[0] else None,
            "stream_id": r[1],
            "track_id": r[2],
            "start_frame_seq": r[3],
            "end_frame_seq": r[4],
            "action_label": r[5],
            "action_confidence": round(float(r[6]), 4),
            "best_frame_seq": r[7],
            "best_frame_score": round(float(r[8]), 4),
            "avg_total_latency_ms": round(float(r[9]), 2),
            "avg_yolo_latency_ms": round(float(r[10]), 2),
            "frame_count": r[11],
        })
    return out
