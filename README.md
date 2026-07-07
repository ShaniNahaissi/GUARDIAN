# GUARDIAN

GUARDIAN is an intelligent real-time video analytics system designed for threat detection in CCTV streams. It leverages an optimized YOLOv8 model for static weapon detection, ByteTrack for persistent tracking, and a lightweight temporal GRU classifier to recognize active threat actions (Shooting, Stabbing, and Violence) over time.

## Quickstart (Development)

- **Backend** (PostgreSQL + API): 
  From repo root, run:
  ```bash
  docker compose -f docker-compose.dev.yml up --build
  ```
- **Frontend**: 
  Navigate to `frontend/app`, install dependencies, and run:
  ```bash
  npm install
  npm run dev -- --host
  ```
  *(The Vite terminal output will display the LAN URL).*

## Production Stack

To build and run the production stack (Postgres + Backend API + Nginx SSL proxy + Dozzle Logs Dashboard):
```bash
docker compose -f docker-compose.yml up --build
```

### Visual Logs UI (Dozzle)
In production, a real-time visual log viewer dashboard is deployed automatically. Open your browser and navigate to:
- **`http://<server-ip>:9999`**
Here you can filter, search, and monitor streaming inference latency (FPS/process ms), CPU utilization, VRAM usage, and active threat alert logs.
