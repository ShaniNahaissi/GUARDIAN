from __future__ import annotations

from fastapi.responses import JSONResponse

from schemas.camera import CameraCreateRequest, CameraInfo, SystemStats

cameras: list[CameraInfo] = []


def list_cameras() -> list[CameraInfo]:
    return cameras


def add_camera(payload: CameraCreateRequest) -> JSONResponse:
    stream_key = (payload.stream_uuid or "").strip()
    camera_id = stream_key if stream_key else f"CAM-{len(cameras) + 1:03d}"
    cameras.append(
        CameraInfo(
            id=camera_id,
            name=payload.name,
            location=payload.location or "",
            imageUrl=(payload.imageUrl or "").strip(),
        )
    )
    return JSONResponse({"ok": True, "id": camera_id})


def compute_stats() -> SystemStats:
    warning = 0
    major = 0
    critical = 0
    for c in cameras:
        if c.status == "warning":
            warning += 1
        elif c.status == "major":
            major += 1
        elif c.status == "critical":
            critical += 1
    return SystemStats(
        activeCameras=len(cameras),
        activeOnline=len(cameras),
        warningAlerts=warning,
        majorAlerts=major,
        criticalAlerts=critical,
    )
