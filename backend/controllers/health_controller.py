import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from bl.detection import state as det_state
from dal.database import engine

logger = logging.getLogger("guardian.audit")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("health.db_ping_failed")
    det = det_state.detector
    return JSONResponse(
        {
            "status": "ok",
            "model_loaded": det is not None,
            "ort_providers": getattr(det, "_providers_used", []) if det else [],
            "database": "ok" if db_ok else "error",
        }
    )
