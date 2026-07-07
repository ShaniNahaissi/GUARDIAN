# AGENT.md — Guardian (repository root)

Onboarding for **new developers** and **AI coding agents**. Read this file first, then **`DEV.md`**, then stack-specific notes under `frontend/AGENT.md` and `backend/AGENT.md`.

## Project goal

Guardian is a proof-of-concept **real-time monitoring** app: camera or edge streams **JPEG frames** to a **Python backend**, **YOLOv8 ONNX** inference detects targets, **ByteTrack** manages identities and smooths bounding boxes, and a **temporal GRU classifier** performs sequence classification to recognize active threats (Shooting, Stabbing, Violence) over a 30-frame window. The **React** UI lists cameras, displays the live feed overlayed with active threat states (e.g. `Suspect (Violence)`), and shows alerts in real-time.

## Architecture

| Layer | Tech | Responsibility |
|-------|------|------------------|
| UI | Vite, React 19, TS, Tailwind v4 | Dashboard, settings, camera view, stream upload page |
| API | FastAPI | REST under **`/api/*`**, health, camera CRUD, stream meta |
| Streams | FastAPI + Starlette | **`WS /producer/{id}`** ingest (JPEG bytes); **`WS /consumer/{id}`** processed JPEG + track JSON; **`GET /consumer/{id}/frame`** JPEG snapshot |
| Inference | ONNX Runtime, supervision ByteTrack, NumPy GRU | Decode → ONNX → tracker smoothing → temporal feature extraction → GRU action classification → draw → broadcast |
| Deploy | Docker, nginx (frontend image), Dozzle | TLS backend; nginx proxies `/api`, `/producer`, `/consumer`, `/health`; Dozzle visual logs UI |

**Critical path**: Producer and consumer must share the **same `stream_id`**. Consumer sockets receive frames only after the producer has sent at least one decodable image for that id.

## Repository map

- **`backend/main.py`** — Single service entrypoint: models, routes, middleware, and WebSocket routers.
- **`backend/bl/detection/pipeline.py`** — Stream processing pipeline compiling YOLOv8 inference, tracker smoothers, early-exit optimizations, static filters, and temporal evaluations.
- **`backend/bl/detection/tracker.py`** — Custom tracking state machine wrapping `supervision.ByteTrack` for zero-lag instant bounding box display and zero weapon ghosting.
- **`backend/bl/detection/temporal_action.py`** — Sequence feature extractor compiling 12D vectors (coords, velocity, weapon/suspect overlaps) and lightweight zero-dependency GRU model in NumPy.
- **`backend/bl/detection/augmentation.py`** — CCTV-realistic transformations (motion blur, digital noise, perspective warp, cutout occlusion).
- **`backend/test_pipeline_upgrades.py`** — Pipeline unit tests validating tracking, early-exits, and static displacement filters.
- **`scripts/train_temporal_action.py`** — PyTorch training script defining the offline sequence training loop, dataset loaders, and weight exporter.
- **`trained_model/guardian_backend_model.onnx`** — Exported YOLOv8 weights path.
- **`trained_model/temporal_action_weights.npz`** — Exported NumPy GRU weights file.
- **`trained_model/names.txt`** — Class names mapping file used to resolve detection IDs (Gun, Knife, Suspect).

## Invariants (do not break without updating docs)

1. **Frontend data access** goes through **`dataService.ts`** (mock vs backend switch via `localStorage` / env).
2. **Stream URLs** — REST lives under **`/api`**; **stream WebSockets and snapshot** live at **origin root**: **`/producer/{id}`**, **`/consumer/{id}`** (WS), **`/consumer/{id}/frame`** (GET).
3. **Dev proxy** — Vite proxies `/api`, `/producer`, `/consumer`, `/health` to **`https://127.0.0.1:8000`** by default.
4. **TypeScript** — `verbatimModuleSyntax`: use `import type` for type-only imports.

## Known bug / gap (document for QA)

**Consumer WebSocket shows “Waiting for frames”**
- The dashboard opens **`WS /consumer/{stream_id}`**; frames appear only after **`WS /producer/{stream_id}`** receives valid **JPEG/PNG** bytes (same id).
- **Root causes to verify**:
  - Producer not running, wrong `stream_id`, or non-image payloads (`imdecode` fails).
  - TLS / mixed-content / wrong origin.
  - Nginx missing `Upgrade` / `Connection` headers for `/consumer` or `/producer`.

## TODO list (backlog)

### Stream / media pipeline
- [ ] **Consumer idle UX**: when `WS /consumer/{id}` has no producer yet, show clearer “no frames” vs error states.
- [ ] Document or implement **chunked video** path if product must use **MediaRecorder WebM**.
- [ ] **HLS** (`.m3u8`) support in **`CameraView`** for Chrome via **hls.js**.
- [ ] **Snapshot fallback**: if the consumer WebSocket is unavailable, poll **`GET /consumer/{id}/frame`** on an interval.

### Backend
- [ ] Persist **cameras** and **stats** (DB or file) instead of in-memory lists.
- [ ] **AuthN/Z** on REST and WebSocket (tokens, stream scoped to tenant).
- [ ] Rate limits and max body size on producer WebSocket.
- [ ] Structured **audit logs** (JSON) + request ID propagation into stream logs.
- [ ] Health check that validates **model load** + optional GPU provider.

### Frontend
- [ ] Replace mock **AuthContext** with real API + secure session/JWT storage.
- [ ] **React Router** (optional) if URL-per-view is required for deep links.
- [ ] E2E tests (Playwright): login mock, add server, verify dashboard list.
- [ ] i18n / a11y audit (sidebar, stream controls, alerts).

### DevEx / CI
- [x] Root **`README.md`** linking quickstart and visual docker log endpoints.
- [x] GitHub Actions: frontend build, backend lint, and unit tests (`pytest`).
- [ ] **mkcert** or small script for trusted local TLS certs on LAN phones.
- [ ] `.env.example` in `frontend/app` with `VITE_BACKEND_URL=/api`.

### Observability
- [x] Real-time metrics dashboard: process latency, input/output bytes, track sizes, CPU utilization, VRAM usage, and active threat log filters.
- [x] Visual logs UI integration (Dozzle) running on port `9999`.
- [ ] Optional OpenTelemetry for FastAPI.
