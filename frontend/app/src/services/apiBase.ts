/** Shared backend API base URL resolution (used by dataService, authApi, etc.). */

export const isBackendEnabled = (): boolean => {
  if (typeof localStorage === 'undefined') return true;
  return localStorage.getItem('guardian_use_backend') !== 'false';
};

/** After TLS migration, old Settings may still store http://localhost:8000/... — upgrade for mixed-content safety. */
export const upgradeLocalHttpBackendUrl = (url: string): string => {
  const trimmed = url.trim();
  if (trimmed.startsWith('/') || !/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(\/|$)/i.test(trimmed)) {
    return trimmed.replace(/^http:/i, 'https:');
  }
  return trimmed;
};

/**
 * In Vite dev, never call loopback :8000 from the browser (http:// breaks TLS-only backend; https:// hits self-signed pain).
 * Use same-origin /api so the dev proxy speaks HTTPS to the backend.
 */
const isLocalViteShell = (): boolean => {
  if (import.meta.env.DEV) return true;
  if (typeof window === 'undefined') return false;
  const { hostname, port } = window.location;
  const loopback = hostname === 'localhost' || hostname === '127.0.0.1';
  const vitePort = port === '5173' || port === '4173';
  return loopback && vitePort;
};

export const coerceDevLoopbackBackendToProxy = (url: string): string => {
  if (!isLocalViteShell() || url.startsWith('/')) return url;
  try {
    const u = new URL(url);
    const loopback = u.hostname === 'localhost' || u.hostname === '127.0.0.1' || u.hostname === '[::1]';
    const portOk = u.port === '' || u.port === '8000';
    if (!loopback || !portOk) return url;
    const p = (u.pathname.replace(/\/$/, '') || '/').toLowerCase();
    if (p === '/api' || p.startsWith('/api/')) {
      return '/api';
    }
  } catch {
    /* ignore */
  }
  return url;
};

export const getBackendUrl = (): string => {
  const fromStorage =
    typeof localStorage !== 'undefined' ? localStorage.getItem('guardian_backend_url') : null;
  let url: string;
  if (fromStorage) {
    url = upgradeLocalHttpBackendUrl(fromStorage);
  } else if (import.meta.env.VITE_BACKEND_URL) {
    url = upgradeLocalHttpBackendUrl(String(import.meta.env.VITE_BACKEND_URL));
  } else if (import.meta.env.DEV) {
    url = '/api';
  } else {
    url = 'https://localhost:8000/api';
  }
  return coerceDevLoopbackBackendToProxy(url);
};
