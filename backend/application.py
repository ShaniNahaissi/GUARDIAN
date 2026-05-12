from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from bl.detection.class_names import load_class_names
from bl.detection.config import MODEL_PATH
from bl.detection import state as det_state
from bl.detection.yolo import YoloOnnxDetector
from bl.seed_service import seed_admin_if_needed
from controllers.admin_controller import router as admin_router
from controllers.auth_controller import router as auth_router
from controllers.cameras_controller import router as cameras_router
from controllers.health_controller import router as health_router
from controllers.streams_controller import router as streams_router
from dal.database import SessionLocal, init_db

logger = logging.getLogger("guardian.audit")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    async with SessionLocal() as session:
        await seed_admin_if_needed(session)

    logger.info("startup.begin model_path=%s", MODEL_PATH)
    det_state.CLASS_NAMES = load_class_names()
    det_state.detector = YoloOnnxDetector(MODEL_PATH, det_state.CLASS_NAMES)
    logger.info(
        "startup.ready model_loaded=%s ort_providers=%s",
        det_state.detector is not None,
        getattr(det_state.detector, "_providers_used", []),
    )
    yield
    logger.info("shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(title="Guardian Backend", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(cameras_router)
    app.include_router(streams_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("https")
    async def audit_latency_middleware(request: Request, call_next: Any) -> Any:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "-")
        path = request.url.path
        query = request.url.query
        full_path = f"{path}?{query}" if query else path

        logger.info(
            "request.start request_id=%s method=%s path=%s client=%s user_agent=%s",
            request_id,
            request.method,
            full_path,
            client_host,
            user_agent,
        )

        try:
            response = await call_next(request)
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request.end request_id=%s method=%s path=%s status=%s latency_ms=%.2f client=%s",
                request_id,
                request.method,
                full_path,
                500,
                latency_ms,
                client_host,
            )
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.end request_id=%s method=%s path=%s status=%s latency_ms=%.2f client=%s",
            request_id,
            request.method,
            full_path,
            response.status_code,
            latency_ms,
            client_host,
        )
        return response

    return app


app = create_app()
