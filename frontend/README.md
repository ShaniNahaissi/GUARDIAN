# Guardian Frontend

A real-time weapon detection monitoring dashboard built with **React**, **TypeScript**, and **Tailwind CSS**. This is the frontend POC for the Guardian security system.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| [Vite](https://vitejs.dev/) | Build tool & dev server |
| [React 19](https://react.dev/) | UI framework |
| [TypeScript](https://www.typescriptlang.org/) | Type-safe JavaScript |
| [Tailwind CSS v4](https://tailwindcss.com/) | Utility-first styling |
| [lucide-react](https://lucide.dev/) | Icon library |

---

## Project Structure

```
frontend/app/src/
├── components/
│   ├── atoms/           # Smallest reusable units (Button, Badge, Card)
│   └── molecules/       # Composite components (Sidebar, StatCard, CameraFeedCard, AlertBanner, ThreatPanel, Tutorial, LiveStreamPreview)
├── context/
│   ├── AuthContext.tsx  # User login/logout/register state using JWT auth
│   ├── ToastContext.tsx # App-wide toast notifications
│   └── StreamingSessionContext.tsx # Stream session tracking
├── layouts/
│   └── MainLayout.tsx   # Shell layout with Sidebar + main content area
├── nav/
│   └── appHash.ts       # Hash-based view router sync helper
├── pages/
│   ├── LoginPage.tsx    # Auth page (login + register)
│   ├── Dashboard.tsx    # Main camera grid view
│   ├── CameraView.tsx   # Single camera focus view with threat panel and snapshot fallback
│   ├── SettingsPage.tsx # Data source configuration and local storage toggles
│   ├── AddCameraPage.tsx# Form to register new cameras
│   ├── EditCameraPage.tsx# Edit camera metadata
│   ├── CameraStreamPage.tsx# Local stream source simulator (device camera/file upload)
│   └── AdminUsersPage.tsx# User accounts configuration dashboard (admin only)
├── services/
│   ├── authApi.ts       # REST client for auth endpoints
│   └── dataService.ts   # Data layer: mock data OR backend API calls
├── App.tsx              # Root component, hash-based routing, auth gate
├── main.tsx             # React entry point
└── index.css            # Global Tailwind v4 styles + theme tokens
```

---

## Getting Started

### Prerequisites
- Node.js 20+
- npm 9+

### Run locally

```bash
cd frontend/app
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

### Build for production

```bash
npm run build
```

Output goes to `dist/`.

---

## Docker

A production-ready Dockerfile is included that builds with Node and serves with nginx.

```bash
# Build the image
docker build -t guardian-frontend ./frontend/app

# Run the container
docker run -p 8080:80 guardian-frontend
```

App will be available at `http://localhost:8080`.

---

## Configuration

### Environment Variables

Create a `.env` file in `frontend/app/`:

```env
# Recommended for `npm run dev`: same-origin `/api` — Vite proxies to the backend (TLS + self-signed cert stay server-side).
VITE_BACKEND_URL=/api

# Only if you do not use the Vite proxy (advanced): browser must trust the backend TLS cert.
# VITE_BACKEND_URL=https://localhost:8000/api
```

All Vite env vars must be prefixed with `VITE_`.

### Mock vs. Backend Data

The app defaults to **Backend API mode**. You can switch to mock data in **Settings > Data Source Configuration** (toggle) or by setting `guardian_use_backend=false` in `localStorage`.

When **Mock** is active, all data comes from hardcoded arrays in `dataService.ts`.  
When **Backend** is active, the app fetches from `VITE_BACKEND_URL`. Backend fetch stubs are clearly marked with comments.

---

## Key Features

| Feature | Where |
|---|---|
| Login / Register | `LoginPage.tsx` |
| Dashboard with camera grid | `Dashboard.tsx` |
| Camera filtering | Dashboard – Filter button |
| Add new camera | `AddCameraPage.tsx` |
| Camera detail + threat panel | `CameraView.tsx` |
| Record / Snapshot | Camera View controls |
| Fullscreen camera view | Camera View – Maximize button |
| Alert notifications (Toast) | `ToastContext.tsx` |
| Settings + backend URL override | `SettingsPage.tsx` |
| In-app tutorial | Sidebar – Help / Tutorial |

---

## Component Architecture

Guardian follows **Atomic Design**:

- **Atoms**: `Button`, `Badge`, `Card` — no logic, only style props.
- **Molecules**: Composed of atoms. May hold local UI state.
- **Pages**: Full views. Consume context and data services.

### State Management

No external state library. Uses React's built-in `useState` and `createContext`:

- `AuthContext` → current user, login, logout, register
- `ToastContext` → global notification queue
- Page-level state → view routing (in `App.tsx`)

---

## Backend Integration

All data fetching lives in `src/services/dataService.ts` and `src/services/authApi.ts`.

Each function checks `isBackendEnabled()`. When true, it does a `fetch()` to the backend. API request headers are loaded with the active JSON Web Token (`Authorization: Bearer <token>`).

**Functional endpoints:**
- `POST /api/auth/login` → `loginRequest()`
- `POST /api/auth/register` → `registerRequest()`
- `GET /api/auth/me` → `fetchMe()`
- `GET /api/cameras` → `getCameras()`
- `POST /api/cameras` → `addCamera()`
- `PUT /api/cameras/{id}` → `updateCamera()`
- `DELETE /api/cameras/{id}` → `deleteCamera()`
- `GET /api/stats` → `getSystemStats()`
- `GET /api/streams/{id}/meta` → `fetchStreamMeta()`

---

## Routing

No `react-router-dom`. Navigation is managed by a `currentView` state string in `App.tsx` and synchronized to the URL hash:

```
'dashboard' | 'camera' | 'settings' | 'add-camera' | 'edit-camera' | 'camera-stream' | 'admin-users'
```

---

## Linting & Type Checking

```bash
npm run build   # Runs tsc -b then vite build
```

All types must pass `tsc` with `verbatimModuleSyntax`. Use `import type` for type-only imports.
