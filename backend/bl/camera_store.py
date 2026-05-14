from __future__ import annotations

from fastapi.responses import JSONResponse

from schemas.camera import CameraCreateRequest, CameraUpdateRequest, CameraInfo, SystemStats

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


def update_camera(camera_id: str, payload: CameraUpdateRequest) -> JSONResponse:
    for i, c in enumerate(cameras):
        if c.id == camera_id:
            cameras[i] = c.model_copy(update={
                "name": payload.name if payload.name is not None else c.name,
                "location": payload.location if payload.location is not None else c.location,
                "imageUrl": payload.imageUrl if payload.imageUrl is not None else c.imageUrl,
            })
            return JSONResponse({"ok": True})
    return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)


def delete_camera(camera_id: str) -> JSONResponse:
    global cameras
    cameras = [c for c in cameras if c.id != camera_id]
    return JSONResponse({"ok": True})


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
