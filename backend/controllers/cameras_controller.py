from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from bl import camera_store
from bl.rbac import CAMERAS_READ, CAMERAS_WRITE, STATS_READ
from dependencies.security import require_permission
from models.user import User
from schemas.camera import CameraCreateRequest, CameraInfo, SystemStats

router = APIRouter(prefix="/api", tags=["cameras"])


@router.get("/cameras", response_model=list[CameraInfo])
async def get_cameras(_user: User = Depends(require_permission(CAMERAS_READ))) -> list[CameraInfo]:
    return camera_store.list_cameras()


@router.post("/cameras")
async def add_camera(
    payload: CameraCreateRequest,
    _user: User = Depends(require_permission(CAMERAS_WRITE)),
) -> JSONResponse:
    return camera_store.add_camera(payload)


@router.get("/stats", response_model=SystemStats)
async def get_stats(_user: User = Depends(require_permission(STATS_READ))) -> SystemStats:
    return camera_store.compute_stats()
