/** Hash-only deep links opened in secondary tabs (#/dashboard) while the Camera Stream tab keeps running. */

const HASH_VIEWS = new Set([
  'dashboard',
  'settings',
  'admin-users',
  'camera-stream',
  'add-camera',
]);

export function parseHashView(): string | null {
  if (typeof window === 'undefined') return null;
  const raw = window.location.hash.replace(/^#\/?/, '').trim().toLowerCase();
  if (!raw || !HASH_VIEWS.has(raw)) return null;
  return raw;
}

export function buildAppUrlForHashView(view: string): string {
  if (typeof window === 'undefined') return `#/${view}`;
  const slug = view.trim().toLowerCase();
  return `${window.location.origin}${window.location.pathname}${window.location.search}#/${slug}`;
}
