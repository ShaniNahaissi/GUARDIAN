# Guardian Backend Agent Notes

## Goal
- Python backend that receives video frames from frontend on a producer route.
- Runs inference with ONNX model: `trained_model/guardian_backend_model.onnx`.
- Exposes processed video on consumer routes for frontend display.

## Stack
- FastAPI + Uvicorn
- ONNX Runtime
- OpenCV + NumPy

## Files
- `backend/main.py`: full backend service.
- `backend/requirements.txt`: Python dependencies.
- `backend/Dockerfile`: container image for consistent backend runtime.
- `backend/Dockerfile.dev`: local dev image with auto-reload.
- `backend/docker-compose.yml`: one-command local container run.
- `backend/docker-compose.dev.yml`: dev compose with bind-mount + auto-reload.

## Routes
- `GET /health`: backend and model status.
- `GET /api/cameras`: camera list for frontend dashboard.
- `POST /api/cameras`: add a camera.
- `GET /api/stats`: simple aggregated stats for frontend.
- `WS /sw/stream/{stream_id}`: producer route (ingest frames).
- `GET /consumer/{stream_id}`: MJPEG consumer stream of processed frames.
- `GET /consumer/{stream_id}/frame`: latest processed frame snapshot (JPEG).
- `GET /api/streams/{stream_id}/meta`: detection metadata (count/max confidence).

## Producer/Consumer Contract
- Producer expects each WebSocket message to be an encoded image frame (`jpeg/png` bytes).
- Backend decodes frame, runs ONNX detection, draws boxes, stores latest processed frame.
- Consumer returns processed output:
  - Continuous MJPEG stream (`/consumer/{stream_id}`)
  - Single latest JPEG frame (`/consumer/{stream_id}/frame`)

## TLS / HTTPS
- Docker images run Uvicorn with **HTTPS on port 8000** by default (self-signed cert generated in-container unless you mount real certs).
- Override with env: `GUARDIAN_TLS_ENABLED=0` for plain HTTP (not recommended if browsers require secure context for camera).
- Custom certs: set `SSL_CERTFILE` and `SSL_KEYFILE` to PEM paths inside the container, and set `GUARDIAN_TLS_AUTO_CERT=0`.
- Entry script: `backend/docker-entrypoint.sh` → copied to `/app/docker-entrypoint.sh` in the image (not under the dev bind mount, so Windows CRLF on repo files does not break `sh`).

## Run (local Python, HTTP — optional)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Run (local Python, HTTPS)
Generate a dev cert (example with OpenSSL), then:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ssl-certfile cert.pem --ssl-keyfile key.pem
```
Or use Docker dev compose, which enables TLS automatically.

## Run With Docker (Recommended for Consistency)
```bash
# From repository root:
docker build -f backend/Dockerfile -t guardian-backend .
docker run --rm -p 8000:8000 guardian-backend
```

Or with compose:
```bash
cd backend
docker compose up --build
```

## Run With Docker (Local Dev Auto-Reload)
```bash
cd backend
docker compose -f docker-compose.dev.yml up --build
```

- Edits in `backend/*.py` trigger automatic server reload.
- **Docker Desktop (Windows/macOS):** bind mounts often do not propagate file-watch events into Linux. Compose sets `WATCHFILES_FORCE_POLLING=true` so Uvicorn’s reloader still sees saves. If reload still fails, restart the backend container after `docker compose build`.
- **Production compose** (`docker-compose.yml` at repo root) does **not** mount source code; rebuild the image to pick up Python changes.
- Stop with `Ctrl+C`, then `docker compose -f docker-compose.dev.yml down`.

## Frontend Integration
- Point `VITE_BACKEND_URL` (or Settings) at `https://localhost:8000/api` when talking to the container or TLS Uvicorn directly. Trust or accept the self-signed certificate in the browser when testing.
- Production Docker: nginx proxies to `https://guardian-backend:8000` with `proxy_ssl_verify off` for the internal self-signed cert.
- Stream WebSocket URL builder uses `wss:` when the API base is `https:`.
- If frontend sends `MediaRecorder` webm chunks, backend cannot decode each chunk as image frame.
- For full real-time detection, frontend should send JPEG frames (for example canvas snapshots) over WebSocket producer route.
