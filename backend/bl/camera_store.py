from __future__ import annotations

from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from dal.database import SessionLocal
from models.camera import Camera
from schemas.camera import CameraCreateRequest, CameraUpdateRequest, CameraInfo, SystemStats


def _to_info(camera: Camera) -> CameraInfo:
    return CameraInfo(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        status=camera.status,
        statusText=camera.statusText,
        imageUrl=camera.imageUrl,
        time=camera.time,
        primaryPhone=getattr(camera, "primaryPhone", "") or "",
        additionalPhone=getattr(camera, "additionalPhone", "") or "",
    )


async def list_cameras() -> list[CameraInfo]:
    async with SessionLocal() as session:
        result = await session.execute(select(Camera))
        return [_to_info(c) for c in result.scalars().all()]


async def add_camera(payload: CameraCreateRequest) -> JSONResponse:
    async with SessionLocal() as session:
        stream_key = (payload.stream_uuid or "").strip()
        if stream_key:
            camera_id = stream_key
        else:
            count = await session.scalar(select(func.count()).select_from(Camera))
            camera_id = f"CAM-{(count or 0) + 1:03d}"

        p_phone = (payload.primaryPhone if payload.primaryPhone is not None else payload.primary_phone) or ""
        a_phone = (payload.additionalPhone if payload.additionalPhone is not None else payload.additional_phone) or ""

        session.add(Camera(
            id=camera_id,
            name=payload.name,
            location=payload.location or "",
            imageUrl=(payload.imageUrl or "").strip(),
            primaryPhone=p_phone.strip(),
            additionalPhone=a_phone.strip(),
        ))
        await session.commit()
    return JSONResponse({"ok": True, "id": camera_id})


async def update_camera(camera_id: str, payload: CameraUpdateRequest) -> JSONResponse:
    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        if camera is None:
            return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
        if payload.name is not None:
            camera.name = payload.name
        if payload.location is not None:
            camera.location = payload.location
        if payload.imageUrl is not None:
            camera.imageUrl = payload.imageUrl
        if payload.primaryPhone is not None:
            camera.primaryPhone = payload.primaryPhone.strip()
        elif payload.primary_phone is not None:
            camera.primaryPhone = payload.primary_phone.strip()
        if payload.additionalPhone is not None:
            camera.additionalPhone = payload.additionalPhone.strip()
        elif payload.additional_phone is not None:
            camera.additionalPhone = payload.additional_phone.strip()
        await session.commit()
    return JSONResponse({"ok": True})


async def delete_camera(camera_id: str) -> JSONResponse:
    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        if camera is not None:
            await session.delete(camera)
            await session.commit()
    return JSONResponse({"ok": True})


async def compute_stats() -> SystemStats:
    async with SessionLocal() as session:
        result = await session.execute(select(Camera.status))
        statuses = [s for (s,) in result.all()]
    return SystemStats(
        activeCameras=len(statuses),
        activeOnline=len(statuses),
        warningAlerts=statuses.count("warning"),
        majorAlerts=statuses.count("major"),
        criticalAlerts=statuses.count("critical"),
    )
