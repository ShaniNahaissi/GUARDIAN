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
│   └── molecules/       # Composite components (Sidebar, StatCard, CameraFeedCard, AlertBanner, ThreatPanel, Tutorial)
├── context/
│   ├── AuthContext.tsx  # User login/logout/register state
│   └── ToastContext.tsx # App-wide toast notifications
├── layouts/
│   └── MainLayout.tsx   # Shell layout with Sidebar + main content area
├── pages/
│   ├── LoginPage.tsx    # Auth page (login + register)
│   ├── Dashboard.tsx    # Main camera grid view
│   ├── CameraView.tsx   # Single camera focus view with threat panel
│   ├── SettingsPage.tsx # Data source configuration
│   └── AddCameraPage.tsx# Form to register new cameras
├── services/
│   └── dataService.ts   # Data layer: mock data OR backend API calls
├── App.tsx              # Root component, routing (state-based), auth gate
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
VITE_BACKEND_URL=http://localhost:8000/api
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

All data fetching lives in `src/services/dataService.ts`.

Each function checks `isBackendEnabled()`. When true, it does a `fetch()` to the backend. Stubs are clearly marked for the next developer to fill in routes.

**Current stubs:**
- `GET /cameras` → `getCameras()`
- `GET /stats` → `getSystemStats()`
- `POST /cameras` → `addCamera()`

---

## Routing

No `react-router-dom`. Navigation is managed by a `currentView` state string in `App.tsx`:

```
'dashboard' | 'camera' | 'settings' | 'add-camera'
```

---

## Linting & Type Checking

```bash
npm run build   # Runs tsc -b then vite build
```

All types must pass `tsc` with `verbatimModuleSyntax`. Use `import type` for type-only imports.
