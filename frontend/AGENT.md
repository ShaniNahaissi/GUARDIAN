# AGENT.md — Guardian Frontend

This file is for AI agents and automated tooling navigating this codebase.

---

## Project Root

```
frontend/
├── app/                  # Vite React-TS application (ALL source code lives here)
│   ├── src/              # Application source
│   ├── public/           # Static assets
│   ├── Dockerfile        # Production Docker build
│   ├── nginx.conf        # nginx SPA config
│   ├── .env              # Local env vars (not committed)
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── vite.config.ts
├── README.md             # Human developer guide
└── AGENT.md              # This file
```

---

## Critical Files (Always Check These First)

| File | Purpose |
|---|---|
| `app/src/App.tsx` | Root component. Routing logic and auth gate live here |
| `app/src/services/dataService.ts` | ALL data access (mock and backend). Add new API calls here |
| `app/src/context/AuthContext.tsx` | User state: `user`, `login`, `logout`, `register` |
| `app/src/context/ToastContext.tsx` | Global toasts: call `useToast().showToast(msg, type)` |
| `app/src/index.css` | Theme tokens (Tailwind v4 `@theme` block). Change colors here |

---

## Routing System

**No react-router.** Navigation is a `useState` in `App.tsx`.

```typescript
// Valid view strings:
'dashboard' | 'camera' | 'settings' | 'add-camera'
```

To add a new page:
1. Create `src/pages/NewPage.tsx`
2. Add new string to the union type in `App.tsx`
3. Add `{currentView === 'new-page' && <NewPage ... />}` in `AppContent`
4. Add a button to `Sidebar.tsx` calling `onNavigate('new-page')`

---

## Data Layer Rules

All data access MUST go through `src/services/dataService.ts`.

```typescript
// Pattern for every new function:
export const myNewFetch = async (): Promise<MyType> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/my-endpoint`);
      if (!res.ok) throw new Error('Failed');
      return await res.json();
    } catch (e) {
      console.error(e);
      return FALLBACK_VALUE;
    }
  }
  return Promise.resolve(MOCK_VALUE);
};
```

`isBackendEnabled()` reads `localStorage.guardian_use_backend`. Default is `true`.  
`getBackendUrl()` reads `localStorage.guardian_backend_url` → falls back to `import.meta.env.VITE_BACKEND_URL` → falls back to `http://localhost:8000/api`.

---

## Component Hierarchy

```
App
└── ToastProvider
    └── AuthProvider
        ├── LoginPage          (shown when user === null)
        └── MainLayout         (shown when user exists)
            ├── Sidebar
            │   └── Tutorial   (modal, activated by Help button)
            └── <current page>
                ├── Dashboard
                ├── CameraView
                ├── SettingsPage
                └── AddCameraPage
```

---

## Adding a New Atom/Molecule

- **Atoms** live in `src/components/atoms/`. No context usage. Props only.
- **Molecules** live in `src/components/molecules/`. May use context (`useToast`, `useAuth`).
- Both must export a named React functional component.

---

## TypeScript Rules

- `verbatimModuleSyntax` is **enabled**. Always use `import type` for type-only imports:
  ```typescript
  import type { MyType } from './types';  // ✅
  import { MyType } from './types';       // ❌ will fail tsc
  ```
- No `any` types.
- Run `npm run build` in `frontend/app` to verify — it runs `tsc -b` + `vite build`.

---

## Styling Rules

- Uses **Tailwind CSS v4** with `@theme` tokens defined in `src/index.css`.
- Custom color tokens: `guardian-bg`, `guardian-card`, `guardian-text`, `guardian-muted`, `guardian-danger`, `guardian-warning`, `guardian-success`, `guardian-accent`.
- Do NOT add Tailwind config to `tailwind.config.js` for colors — use `@theme` in `index.css` instead (Tailwind v4 pattern).

---

## Auth Pattern

```typescript
import { useAuth } from '../context/AuthContext';
const { user, login, logout, register } = useAuth();
```

`user` is `null` when logged out. `App.tsx` gates all pages behind `user !== null`.  
Currently mock auth — any username/password works. Replace `login()` body in `AuthContext.tsx` with real API call.

---

## Toast Notifications

```typescript
import { useToast } from '../context/ToastContext';
const { showToast } = useToast();

showToast('Camera added!', 'success');  // types: 'success' | 'error' | 'info'
```

---

## Build & Run

```bash
# Dev server
cd frontend/app && npm run dev

# Production build (also type-checks)
cd frontend/app && npm run build

# Docker
docker build -t guardian-frontend ./frontend/app
docker run -p 8080:80 guardian-frontend
```
