# Guardian Backend Agent Notes

## Goal
- Python FastAPI backend that receives video frames from frontend on a producer route.
- Runs inference with ensembled YOLOv8 models: custom static weapon detector (`trained_model/guardian_backend_model.onnx`) and COCO person detector (`trained_model/yolov8n_person.onnx`) with remapping.
- App-side cross-model Non-Maximum Suppression (NMS) to merge overlapping suspect bounding boxes.
- ByteTrack (via `supervision`) assigns persistent `track_id` across weapons and suspects.
- A lightweight NumPy CNN temporal action classifier determines active threats (Shooting/Violence) over a 30-frame window.
- Database integration logging frame metrics (latency, tracks, CPU/GPU, VRAM usage).
- Consumers receive processed JPEG + JSON over WebSocket, or poll single snapshots.

## Files
- `backend/main.py`: ASGI server entrypoint that runs the FastAPI `app` from `application.py`.
- `backend/application.py`: application bootstrap, models loading, CORS setup, DB seeding/init, and request latency audit middleware.
- `backend/requirements.txt`: Python dependencies.
- `backend/Dockerfile`: production container image.
- `backend/Dockerfile.dev`: local dev image with auto-reload.
- `backend/docker-compose.yml`: production-style multi-container setup.
- `backend/docker-compose.dev.yml`: dev compose with bind-mount + auto-reload.

## Routes
- **Authentication**:
  - `POST /api/auth/login`: verifies user credentials, returns JWT token.
  - `POST /api/auth/register`: registers new user, returns JWT token.
  - `GET /api/auth/me`: retrieves current authenticated user profile.
- **Cameras (CRUD & Stats)**:
  - `GET /api/cameras`: list cameras.
  - `POST /api/cameras`: add a camera.
  - `PUT /api/cameras/{camera_id}`: update camera.
  - `DELETE /api/cameras/{camera_id}`: remove camera.
  - `GET /api/stats`: system aggregated stats for the dashboard.
- **Streams (Producer & Consumer)**:
  - `WS /producer/{stream_id}`: producer ingest (**binary JPEG or PNG per message**). Runs the detection pipeline and broadcasts to consumers.
  - `WS /consumer/{stream_id}`: consumer stream — for each processed frame the server sends **(1) binary** processed JPEG bytes, then **(2) text JSON** with `{ stream_id, frame_seq, tracks: [{ track_id, bbox, class_name, confidence }], yolo_latency_ms, person_latency_ms, action_latency_ms, pipeline_latency_ms }`.
  - `GET /consumer/{stream_id}/frame`: latest processed JPEG snapshot (404 until a frame exists).
  - `GET /api/streams/{stream_id}/meta`: active detection counts (weapon_count, confirmed_threat flag, etc.) stored in memory.

## Pipeline & Model Customization
- **Dual Model Inference**: Remaps class `person` (0) from the secondary COCO detector to class `Suspect` (2) to bolster suspect detection recall alongside the custom weapon detector. Bounding boxes are filtered using OpenCV DNN NMS.
- **Temporal Action Classifier**: A 1D-CNN temporal action classifier loads weight parameters from `trained_model/temporal_action_weights.npz` (application fail-fast startup check if weights are missing) and operates on a 30-frame sequence window.
- **Static Displacement Filter**: Static tracks with a displacement lower than 2% of the frame dimensions over the history window default to action class "Normal" (short-circuiting action classification to save CPU), EXCEPT when a weapon has been seen inside the temporal window history (weapon-aware override).

## Pipeline Configuration & Tuning (bl/detection/config.py)
The following configuration variables can be tweaked via environment variables:
- `GUARDIAN_WEAPON_CONF_THRESHOLD` (default: `0.25`): minimum confidence for custom model detections.
- `GUARDIAN_WEAPON_IOU_THRESHOLD` (default: `0.7`): IoU threshold for YOLO NMS.
- `GUARDIAN_ENHANCE_DETECTION_INPUT` (default: `true`): applies CLAHE contrast adjustment and unsharp mask sharpening on the detector frame input only.
- `GUARDIAN_ACTION_CONF_THRESHOLD` (default: `0.50`): minimum classification probability threshold required to override a track's status with an active threat label (Shooting/Violence).
- `GUARDIAN_BBOX_SMOOTH_ALPHA` (default: `0.6`): Exponential Moving Average (EMA) factor for bbox coordinate smoothing (lower is smoother, higher is more responsive).
- `GUARDIAN_WEAPON_GHOST_FRAMES` (default: `3`): number of missed-detection frames a weapon track remains alive.
- `GUARDIAN_SUSPECT_GHOST_FRAMES` (default: `5`): number of missed-detection frames a suspect track remains alive.
- `GUARDIAN_CONFIDENCE_DECAY` (default: `0.85`): score degradation multiplier applied per missed frame on ghost tracks.

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
