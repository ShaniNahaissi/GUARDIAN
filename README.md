# GUARDIAN

For dev:

- **Backend** (PostgreSQL + API): from repo root, `docker compose -f docker-compose.dev.yml up --build`
- **Frontend**: `cd frontend\app`, `npm install`, then `npm run dev -- --host` (serves on the LAN; the terminal shows the URL)

Production stack (Postgres + backend + TLS nginx): `docker compose -f docker-compose.yml up --build`
