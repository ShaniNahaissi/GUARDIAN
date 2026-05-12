# Guardian — Developer guide

Orientation for humans running and changing the Guardian stack (weapon-detection POC: ingest → ONNX → dashboards / streams).

## What this repo is

- **Backend**: FastAPI + Uvicorn (HTTPS in Docker by default), ONNX Runtime + OpenCV + supervision ByteTrack, in-memory frame store, WebSocket producer/consumer and JPEG snapshot route.
- **Frontend**: Vite + React + TypeScript + Tailwind v4, mock-or-backend data layer, no React Router (view state in `App.tsx`).
- **Ops**: Docker Compose for backend (and optional full stack), nginx in the production frontend image proxying `/api`, `/producer`, `/consumer`, `/health` to the backend.

## Repository layout

```
GUARDIAN/
├── backend/           # Python service (main.py, Dockerfile, entrypoint TLS)
├── frontend/
│   ├── app/           # Vite React app (all UI source)
│   └── AGENT.md       # Frontend-specific agent notes
├── trained_model/     # ONNX model path expected by backend
├── docker-compose.yml # Production-style stack
├── docker-compose.dev.yml
└── scripts/           # docker-up helpers
```

## Architecture (data flow)

```mermaid
flowchart LR
  subgraph ingest [Ingest]
    FE_CAM[Camera / Stream UI]
    WS["WS /producer/{id}"]
  end
  subgraph backend [Backend]
    DEC[Decode JPEG frame]
    ONNX[ONNX detect]
    BT[ByteTrack]
    DRAW[Draw boxes]
    STORE[(StreamStore)]
    BCAST[Broadcast consumers]
  end
  subgraph consume [Consume]
    CWS["WS /consumer/{id}"]
    SNAP["GET /consumer/{id}/frame"]
  end
  FE_CAM --> WS
  WS --> DEC --> ONNX --> BT --> DRAW --> STORE
  DRAW --> BCAST
  BCAST --> CWS
  STORE --> SNAP
```

- **Producer contract**: WebSocket messages should be **decodable image bytes** (e.g. JPEG/PNG), one frame per message. The Camera Stream page sends **canvas JPEG** snapshots at a fixed interval.
- **Consumer contract**: `WS /consumer/{stream_id}` delivers **binary JPEG** then **JSON** `{ stream_id, frame_seq, tracks: [...] }` per processed frame. The **same** `stream_id` must be used on the producer, consumer, and when registering cameras in the UI. **`GET /consumer/{stream_id}/frame`** returns the latest JPEG (404 until a frame exists).

## Local development

### Backend

From `backend/` (see `backend/AGENT.md`):

- Venv, `pip install -r requirements.txt`, run Uvicorn (with or without TLS per entrypoint docs).
- Docker: `docker compose` files in repo root and `backend/`.

### Frontend

From `frontend/app/`:

- `npm install`
- `npm run dev -- --host` — dev server uses HTTPS (basic SSL plugin) and proxies `/api`, `/producer`, `/consumer`, `/health` to `GUARDIAN_API_PROXY` (default `https://127.0.0.1:8000`).

**Settings / API URL in dev**: Prefer **`/api`** so the browser stays same-origin and the Vite proxy terminates TLS to the backend. Direct `https://localhost:8000/api` from the browser can hit self-signed certificate friction.

Details: `frontend/AGENT.md`, `frontend/README.md`.

## Known issue: consumer shows no live image

Symptoms: Dashboard or camera view stays on **“Waiting for frames”** for a `stream_id`.

Likely causes (check in order):

1. **No producer for that id** — Open **`WS /producer/{stream_id}`** (Camera Stream page) and send JPEG frames; until `imdecode` succeeds, consumers receive nothing.
2. **`stream_id` mismatch** — Producer, consumer, and camera registration must use the **same** id (watch URL encoding).
3. **Wrong payload on producer** — Non-image binary causes decode skip; use the in-app JPEG pump or valid image bytes.
4. **Proxy / WebSocket** — Vite and nginx must forward **`Upgrade`** and **`Connection`** for `/producer` and `/consumer`.
5. **TLS / mixed content** — Page `https:` must use `wss:` to the same origin or trusted proxy.

**Action items** for follow-up are tracked in the root **`AGENT.md`** TODO list.

## Related docs

| Doc | Audience |
|-----|----------|
| `AGENT.md` (repo root) | Agents + leads: invariants, TODOs, read order |
| `frontend/AGENT.md` | Frontend structure, routing, `dataService` rules |
| `backend/AGENT.md` | API routes, producer/consumer contract, run commands |
| `frontend/README.md` | Human-focused frontend setup |

## Security note

This is a **POC**: mock auth, permissive CORS in backend, self-signed TLS in dev/Docker. Do not expose as-is to the public internet without hardening.
