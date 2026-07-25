from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from bl import camera_store
from bl.rbac import CAMERAS_READ, CAMERAS_WRITE, STATS_READ
from dependencies.security import require_permission
from models.user import User
from schemas.camera import CameraCreateRequest, CameraUpdateRequest, CameraInfo, SystemStats

router = APIRouter(prefix="/api", tags=["cameras"])


@router.get("/cameras", response_model=list[CameraInfo])
async def get_cameras(_user: User = Depends(require_permission(CAMERAS_READ))) -> list[CameraInfo]:
    return await camera_store.list_cameras()


@router.post("/cameras")
async def add_camera(
    payload: CameraCreateRequest,
    _user: User = Depends(require_permission(CAMERAS_WRITE)),
) -> JSONResponse:
    return await camera_store.add_camera(payload)


@router.put("/cameras/{camera_id}")
async def edit_camera(
    camera_id: str,
    payload: CameraUpdateRequest,
    _user: User = Depends(require_permission(CAMERAS_WRITE)),
) -> JSONResponse:
    return await camera_store.update_camera(camera_id, payload)


@router.delete("/cameras/{camera_id}")
async def remove_camera(
    camera_id: str,
    _user: User = Depends(require_permission(CAMERAS_WRITE)),
) -> JSONResponse:
    return await camera_store.delete_camera(camera_id)


@router.get("/stats", response_model=SystemStats)
async def get_stats(_user: User = Depends(require_permission(STATS_READ))) -> SystemStats:
    return await camera_store.compute_stats()
