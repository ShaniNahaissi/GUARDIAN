# AGENT.md — Guardian (repository root)

Onboarding for **new developers** and **AI coding agents**. Read this file first, then **`DEV.md`**, then stack-specific notes under `frontend/AGENT.md` and `backend/AGENT.md`.

## Project goal

Guardian is a proof-of-concept **real-time monitoring** app: camera or edge streams frames to a **Python backend**, **ONNX** inference draws detections, and the **React** UI lists cameras, shows a processed **MJPEG** feed, and supports WebSocket ingest.

## Architecture (short)

| Layer | Tech | Responsibility |
|-------|------|------------------|
| UI | Vite, React 19, TS, Tailwind v4 | Dashboard, settings, camera view, stream upload page |
| API | FastAPI | REST under **`/api/*`**, health, camera CRUD, stream meta |
| Streams | FastAPI + Starlette | **`WS /sw/stream/{id}`** ingest; **`GET /consumer/{id}`** MJPEG out; **`GET /consumer/{id}/frame`** JPEG snapshot |
| Inference | ONNX Runtime, OpenCV, NumPy | Decode frame → run model → draw boxes → store latest processed JPEG |
| Deploy | Docker, nginx (frontend image) | TLS backend; nginx proxies `/api`, `/sw`, `/consumer` to backend |

**Critical path**: Producer and consumer must share the **same `stream_id`**. Consumer output exists only after the backend has **stored** a processed frame for that id.

## Repository map

- **`backend/main.py`** — Single service: models, routes, middleware (audit/latency), WebSocket producer, MJPEG consumer.
- **`frontend/app/src/services/dataService.ts`** — **Only** place for API/stream URL helpers (`getBackendUrl`, `getConsumerMjpegUrl`, WebSocket URL builder, add camera payload).
- **`frontend/app/src/App.tsx`** — View state machine (`dashboard` | `camera` | `settings` | `add-camera` | `camera-stream`); no `react-router`.
- **`trained_model/guardian_backend_model.onnx`** — Expected model path (see backend startup).

## Invariants (do not break without updating docs)

1. **Frontend data access** goes through **`dataService.ts`** (mock vs backend switch via `localStorage` / env).
2. **Stream URLs** — REST lives under **`/api`**; **MJPEG and WebSocket** live at **origin root**: **`/consumer/{id}`**, **`/sw/stream/{id}`** (not under `/api`).
3. **Dev proxy** — Vite proxies `/api`, `/sw`, `/consumer`, `/health` to **`https://127.0.0.1:8000`** by default (`GUARDIAN_API_PROXY` override).
4. **TypeScript** — `verbatimModuleSyntax`: use `import type` for type-only imports.

## Known bug / gap (document for QA)

**Stream consume not working — Network status stuck in Pending**

- Observed when opening **`GET /consumer/{stream_id}`** (or same-origin proxied URL) in the browser: request remains **Pending** in DevTools.
- **Root causes to verify** (see **`DEV.md`**):
  - No processed frames in **`StreamStore`** for that id (producer not sending valid **image** bytes, or id mismatch).
  - MJPEG long-poll / proxy buffering behavior.
  - TLS / mixed-content / wrong base URL.
- **Next engineering steps**: Add backend metrics or logging when the consumer connects but `get_processed` is empty for N seconds; consider sending an initial placeholder frame or HTTP 204/503 policy; verify Vite proxy streaming; add E2E test with synthetic JPEG over WS then assert consumer headers/body.

## Suggested read order

1. `DEV.md` (human runbook + architecture)
2. `frontend/AGENT.md` (UI patterns, build)
3. `backend/AGENT.md` (routes, Docker TLS, producer contract)

## TODO list (backlog)

### Stream / media pipeline

- [ ] **Fix consumer Pending**: reproduce with one `stream_id`; confirm `store.processed_frames[id]` updates; fix producer payload or consumer idle behavior.
- [ ] Document or implement **chunked video** path if product must use **MediaRecorder WebM** (transcode server-side or switch client to **JPEG snapshots** over WS).
- [ ] **HLS** (`.m3u8`) support in **`CameraView`** for Chrome via **hls.js** (Safari native).
- [ ] **Snapshot fallback**: if MJPEG fails in `<img>`, try **`/consumer/{id}/frame`** on an interval (already exposed in `dataService`).

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

- [ ] Root **`README.md`** linking `DEV.md` + quickstart one-liners.
- [ ] GitHub Actions: `frontend npm run build`, `backend` lint + `pytest` (when tests exist).
- [ ] **mkcert** or small script for trusted local TLS certs on LAN phones.
- [ ] `.env.example` in `frontend/app` with `VITE_BACKEND_URL=/api`, `GUARDIAN_API_PROXY=...`

### Security / prod

- [ ] Remove or lock down **CORS** `*` for production.
- [ ] Secrets management for any future cloud deploy.
- [ ] Nginx / API gateway: timeouts and body limits for **`/consumer`** long streams.

### Observability

- [ ] Metrics: frames in/out per `stream_id`, inference latency histogram.
- [ ] Optional OpenTelemetry for FastAPI.

---

When you close an item above, update this file or **`DEV.md`** so the next dev inherits current truth.
