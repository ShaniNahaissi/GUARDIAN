# AGENT.md — Guardian (repository root)

Onboarding for **new developers** and **AI coding agents**. Read this file first, then **`DEV.md`**, then stack-specific notes under `frontend/AGENT.md` and `backend/AGENT.md`.

## Project goal

Guardian is a proof-of-concept **real-time monitoring** app: camera or edge streams **JPEG frames** to a **Python backend**, **ONNX** inference plus **ByteTrack** produce detections with persistent IDs, and the **React** UI lists cameras, shows a processed feed via **WebSocket consumer** (binary JPEG + JSON), and supports WebSocket producer ingest.

## Architecture (short)

| Layer | Tech | Responsibility |
|-------|------|------------------|
| UI | Vite, React 19, TS, Tailwind v4 | Dashboard, settings, camera view, stream upload page |
| API | FastAPI | REST under **`/api/*`**, health, camera CRUD, stream meta |
| Streams | FastAPI + Starlette | **`WS /producer/{id}`** ingest (JPEG bytes); **`WS /consumer/{id}`** processed JPEG + track JSON; **`GET /consumer/{id}/frame`** JPEG snapshot |
| Inference | ONNX Runtime, OpenCV, NumPy, supervision ByteTrack | Decode → ONNX → track → draw → broadcast |
| Deploy | Docker, nginx (frontend image) | TLS backend; nginx proxies `/api`, `/producer`, `/consumer`, `/health` to backend |

**Critical path**: Producer and consumer must share the **same `stream_id`**. Consumer sockets receive frames only after the producer has sent at least one decodable image for that id.

## Repository map

- **`backend/main.py`** — Single service: models, routes, middleware (audit/latency), WebSocket producer/consumer, ONNX + ByteTrack.
- **`frontend/app/src/services/dataService.ts`** — **Only** place for API/stream URL helpers (`getBackendUrl`, `getProducerWebSocketUrl`, `getConsumerWebSocketUrl`, `getConsumerSnapshotUrl`, add camera payload).
- **`frontend/app/src/App.tsx`** — View state machine (`dashboard` | `camera` | `settings` | `add-camera` | `camera-stream`); no `react-router`.
- **`trained_model/guardian_backend_model.onnx`** — Expected model path (see backend startup).

## Invariants (do not break without updating docs)

1. **Frontend data access** goes through **`dataService.ts`** (mock vs backend switch via `localStorage` / env).
2. **Stream URLs** — REST lives under **`/api`**; **stream WebSockets and snapshot** live at **origin root**: **`/producer/{id}`**, **`/consumer/{id}`** (WS), **`/consumer/{id}/frame`** (GET) (not under `/api`).
3. **Dev proxy** — Vite proxies `/api`, `/producer`, `/consumer`, `/health` to **`https://127.0.0.1:8000`** by default (`GUARDIAN_API_PROXY` override).
4. **TypeScript** — `verbatimModuleSyntax`: use `import type` for type-only imports.

## Known bug / gap (document for QA)

**Consumer WebSocket shows “Waiting for frames”**

- The dashboard opens **`WS /consumer/{stream_id}`**; frames appear only after **`WS /producer/{stream_id}`** receives valid **JPEG/PNG** bytes (same id).
- **Root causes to verify** (see **`DEV.md`**):
  - Producer not running, wrong `stream_id`, or non-image payloads (`imdecode` fails).
  - TLS / mixed-content / wrong origin (use same-origin proxied URLs in Vite dev).
  - Nginx missing `Upgrade` / `Connection` headers for `/consumer` or `/producer`.
- **Next engineering steps**: Metrics for frames in/out per `stream_id`; optional placeholder JPEG on first consumer connect; Playwright E2E with synthetic JPEG over producer WS.

## Suggested read order

1. `DEV.md` (human runbook + architecture)
2. `frontend/AGENT.md` (UI patterns, build)
3. `backend/AGENT.md` (routes, Docker TLS, producer contract)

## TODO list (backlog)

### Stream / media pipeline

- [ ] **Consumer idle UX**: when `WS /consumer/{id}` has no producer yet, show clearer “no frames” vs error states; optional placeholder frame from backend.
- [ ] Document or implement **chunked video** path if product must use **MediaRecorder WebM** (transcode server-side or switch client to **JPEG snapshots** over WS).
- [ ] **HLS** (`.m3u8`) support in **`CameraView`** for Chrome via **hls.js** (Safari native).
- [ ] **Snapshot fallback**: if the consumer WebSocket is unavailable, poll **`GET /consumer/{id}/frame`** on an interval (see `getConsumerSnapshotUrl` in `dataService.ts`).

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
