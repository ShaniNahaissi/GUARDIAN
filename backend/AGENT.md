# Guardian Backend Agent Notes

## Goal
- Python backend that receives video frames from frontend on a producer route.
- Runs inference with ONNX model: `trained_model/guardian_backend_model.onnx`.
- ByteTrack (via `supervision`) assigns persistent `track_id` per `stream_id`.
- Consumers receive processed JPEG + JSON over WebSocket.

## Stack
- FastAPI + Uvicorn
- ONNX Runtime (CPU or CUDA when available)
- OpenCV + NumPy
- `supervision` (ByteTrack): Trackers are tied to the producer's session and reset automatically on reconnect to prevent stale ghost tracks. The internal `lost_track_buffer` is kept synchronized with the custom ghost frame settings.

## Files
- `backend/main.py`: full backend service.
- `backend/requirements.txt`: Python dependencies.
- `backend/Dockerfile`: container image for consistent backend runtime.
- `backend/Dockerfile.dev`: local dev image with auto-reload.
- `backend/docker-compose.yml`: one-command local container run.
- `backend/docker-compose.dev.yml`: dev compose with bind-mount + auto-reload.

## Routes
- `GET /health`: backend, model, and ORT provider status.
- `GET /api/cameras`: camera list for frontend dashboard.
- `POST /api/cameras`: add a camera.
- `GET /api/stats`: simple aggregated stats for the frontend.
- `WS /producer/{stream_id}`: producer ingest (**binary JPEG or PNG per message**).
- `WS /consumer/{stream_id}`: consumer stream — for each processed frame the server sends **(1) binary** processed JPEG bytes, **(2) text JSON** with `{ stream_id, frame_seq, tracks: [{ track_id, bbox, class_name, confidence }] }`.
- `GET /consumer/{stream_id}/frame`: latest processed JPEG snapshot (404 until a frame exists).
- `GET /api/streams/{stream_id}/meta`: detection metadata (count / max confidence).

## Producer / consumer contract
- Producer: each WebSocket message is **one encoded image** (`jpeg`/`png` bytes). The backend decodes with `cv2.imdecode`, runs ONNX + ByteTrack, draws boxes, then broadcasts to all consumer sockets for that `stream_id`.
- Consumer WebSocket: messages arrive in **pairs** (binary JPEG, then JSON). Clients should use the same `stream_id` as the producer.
- Snapshot: `GET /consumer/{stream_id}/frame` returns a single JPEG body.

## Class names
- Optional env `GUARDIAN_CLASS_NAMES` as `0:knife,1:gun` (comma-separated `id:name`).
- Optional `trained_model/names.txt` (one name per line, 0-based index).

## ORT providers
- Set `GUARDIAN_ORT_CUDA=0` to force CPU only.
- Set `GUARDIAN_ORT_TRT=1` to allow TensorRT when the build supports it.

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
- Producer WebSocket URL builder: `wss:` when the page is `https:`.
- If the frontend sends non-image binary, `imdecode` fails and that frame is skipped.
