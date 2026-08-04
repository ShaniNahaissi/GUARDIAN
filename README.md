# GUARDIAN

GUARDIAN is an intelligent near real-time video analytics system designed for threat detection in CCTV streams. It integrates a dual-detector pipeline—combining a pretrained person detection model with a custom-trained YOLOv8 weapon model—for static threat localization, ByteTrack for persistent tracking, and a lightweight temporal 1D-CNN classifier (leveraging local temporal feature extraction, inference speed efficiency, and parallel hardware optimization over RNNs) to recognize active threat actions (Shooting and Violence) over time.

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
In production, a near real-time visual log viewer dashboard is deployed automatically. Open your browser and navigate to:
- **`http://<server-ip>:9999`**
Here you can filter, search, and monitor streaming inference latency (FPS/process ms), CPU utilization, VRAM usage, and active threat alert logs.

## Note on Documentation
The `old/` directory contains legacy/older versions of documentation (such as `old/GUARDIAN_Final_Project_Book.docx`). The current compiled Word document is `GUARDIAN_Final_Project_Book_New.docx` at the root.
