# AGENTS.md — Guardian (repository root)

Onboarding for **new developers** and **AI coding agents**. Read this file first, then **`DEV.md`**, then stack-specific notes under `frontend/AGENT.md` and `backend/AGENT.md`.

## Project goal

Guardian is a proof-of-concept **near real-time monitoring** app: camera or local streams **JPEG frames** to a **Python backend**, **YOLOv8 ONNX** inference detects targets, **ByteTrack** manages identities and smooths bounding boxes, and a **temporal 1D-CNN classifier** performs sequence classification to recognize active threats (Shooting, Violence) over a 30-frame window. The **React** UI lists cameras, displays the live feed overlayed with active threat states (e.g. `Suspect (Violence)`), and shows alerts in near real-time.

## Architecture

| Layer | Tech | Responsibility |
|-------|------|------------------|
| UI | Vite, React 19, TS, Tailwind v4 | Dashboard, settings, camera view, stream upload page |
| API | FastAPI | REST under **`/api/*`**, health, camera CRUD, stream meta |
| Streams | FastAPI + Starlette | **`WS /producer/{id}`** ingest (JPEG bytes); **`WS /consumer/{id}`** processed JPEG + track JSON; **`GET /consumer/{id}/frame`** JPEG snapshot |
| Inference | ONNX Runtime, supervision ByteTrack, NumPy CNN | Decode → ONNX → tracker smoothing → temporal feature extraction → CNN action classification → draw → broadcast |
| Deploy | Docker, nginx (frontend image), Dozzle | TLS backend; nginx proxies `/api`, `/producer`, `/consumer`, `/health`; Dozzle visual logs UI |

**Critical path**: Producer and consumer must share the **same `stream_id`**. Consumer sockets receive frames only after the producer has sent at least one decodable image for that id.

## Repository map

- **`backend/main.py`** — ASGI entrypoint proxying to `application.py`.
- **`backend/application.py`** — Application bootstrap: loads models (YOLOv8 custom and person detectors), sets up DB lifespan init/seeding, CORSMiddleware, and request latency/audit middleware.
- **`backend/bl/detection/pipeline.py`** — Stream processing pipeline compiling YOLOv8 inference (with CLAHE/sharpening input enhancement), double-detector merging (weapon model + person model remapping), cross-model NMS deduplication, tracker smoothing, early-exit displacement filters, and temporal evaluations via 1D-CNN.
- **`backend/bl/detection/tracker.py`** — Custom tracking state machine wrapping `supervision.ByteTrack` for zero-lag instant bounding box display, independent weapon (3 frames) / suspect (5 frames) survival ghost windows, EMA-smoothed coordinates, and confidence decay.
- **`backend/bl/detection/temporal_action.py`** — Sequence feature extractor compiling 12D vectors (coords, velocity, weapon/suspect overlaps) and lightweight zero-dependency 1D-CNN model in NumPy.
- **`backend/bl/detection/augmentation.py`** — CCTV-realistic transformations (motion blur, digital noise, perspective warp, cutout occlusion).
- **`backend/test_pipeline_upgrades.py`** — Pipeline unit tests validating tracking, early-exits, and static displacement filters.
- **`temporal_training/`** — Self-contained UCF-Crime dataset builder + notebook that trains the 1D-CNN temporal action classifier and exports its weights (see `temporal_training/temporal_training.ipynb`).
- **`trained_model/guardian_backend_model.onnx`** — Exported YOLOv8 weights path.
- **`trained_model/yolov8n_person.onnx`** — Pretrained COCO person detection model.
- **`trained_model/temporal_action_weights.npz`** — Exported NumPy CNN weights file (conv1_w/conv1_b/conv2_w/conv2_b/fc_w/fc_b). Application fails to start if missing.
- **`trained_model/names.txt`** — Class names mapping file used to resolve detection IDs (Gun, Knife, Suspect).

## Invariants (do not break without updating docs)

1. **Frontend data access** goes through **`dataService.ts`** (mock vs backend switch via `localStorage` / env).
2. **Stream URLs** — REST lives under **`/api`**; **stream WebSockets and snapshot** live at **origin root**: **`/producer/{id}`**, **`/consumer/{id}`** (WS), **`/consumer/{id}/frame`** (GET).
3. **Dev proxy** — Vite proxies `/api`, `/producer`, `/consumer`, `/health` to **`https://127.0.0.1:8000`** by default.
4. **TypeScript** — `verbatimModuleSyntax`: use `import type` for type-only imports.
5. **Deprecated / Legacy Files** — The `old/` directory contains deprecated, older versions of documentation (such as `old/GUARDIAN_Final_Project_Book.docx`). The current compiled Word document is `GUARDIAN_Final_Project_Book_New.docx` at the root.

## Known bug / gap (document for QA)

**Consumer WebSocket shows “Waiting for frames”**
- The dashboard opens **`WS /consumer/{stream_id}`**; frames appear only after **`WS /producer/{stream_id}`** receives valid **JPEG/PNG** bytes (same id).
- **Root causes to verify**:
  - Producer not running, wrong `stream_id`, or non-image payloads (`imdecode` fails).
  - TLS / mixed-content / wrong origin.
  - Nginx missing `Upgrade` / `Connection` headers for `/consumer` or `/producer`.

## TODO list (backlog)

### Stream / media pipeline
- [x] **Background capture tick worker**: Dedicated Web Worker tick loop in frontend (`CameraStreamPage.tsx`) to prevent browser throttling when the stream tab is backgrounded/minimized.
- [ ] **Consumer idle UX**: when `WS /consumer/{id}` has no producer yet, show clearer “no frames” vs error states.
- [ ] Document or implement **chunked video** path if product must use **MediaRecorder WebM**.
- [ ] **HLS** (`.m3u8`) support in **`CameraView`** for Chrome via **hls.js**.
- [ ] **Snapshot fallback**: if the consumer WebSocket is unavailable, poll **`GET /consumer/{id}/frame`** on an interval.

### Backend
- [x] Persist **cameras** and **stats** in Postgres (`models/camera.py`, `bl/camera_store.py`) instead of in-memory lists.
- [x] **AuthN/Z** on REST endpoints (JWT validation, custom permissions); WebSockets (/producer & /consumer) still bypass token validation.
- [ ] Rate limits and max body size on producer WebSocket.
- [ ] Structured **audit logs** (JSON) + request ID propagation into stream logs.
- [ ] Health check that validates **model load** + optional GPU provider.

### Frontend
- [x] Replace mock **AuthContext** with real API + secure session/JWT storage (via localStorage).
- [x] **Custom Hash Routing**: Custom hash synchronization (`src/nav/appHash.ts`) syncing views with URL hashes (e.g. `#/dashboard`) without React Router.
- [ ] E2E tests (Playwright): login mock, add server, verify dashboard list.
- [ ] i18n / a11y audit (sidebar, stream controls, alerts).

### DevEx / CI
- [x] Root **`README.md`** linking quickstart and visual docker log endpoints.
- [x] GitHub Actions: frontend build, backend lint, and unit tests (`pytest`).
- [ ] **mkcert** or small script for trusted local TLS certs on LAN phones.
- [ ] `.env.example` in `frontend/app` with `VITE_BACKEND_URL=/api`.

### Observability
- [x] Near real-time metrics dashboard: process latency, input/output bytes, track sizes, CPU utilization, VRAM usage, and active threat log filters.
- [x] Visual logs UI integration (Dozzle) running on port `9999`.
- [ ] Optional OpenTelemetry for FastAPI.
