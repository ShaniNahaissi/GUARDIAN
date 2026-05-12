import { getBackendUrl } from './apiBase';
import { getStoredAccessToken, type AppRole } from './authApi';

export interface AdminUserRow {
  id: string;
  username: string;
  fullName: string;
  role: AppRole;
  createdAt: string | null;
}

const headersJson = (): HeadersInit => {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  const t = getStoredAccessToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
};

async function parseDetail(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d))
      return d.map((x: { msg?: string }) => x?.msg || JSON.stringify(x)).join('; ');
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status})`;
}

export async function listAdminUsers(): Promise<AdminUserRow[]> {
  const res = await fetch(`${getBackendUrl()}/admin/users`, { headers: headersJson() });
  if (!res.ok) throw new Error(await parseDetail(res));
  return res.json() as Promise<AdminUserRow[]>;
}

export async function createAdminUser(payload: {
  username: string;
  password: string;
  full_name: string;
  role: AppRole;
}): Promise<AdminUserRow> {
  const res = await fetch(`${getBackendUrl()}/admin/users`, {
    method: 'POST',
    headers: headersJson(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseDetail(res));
  return res.json() as Promise<AdminUserRow>;
}

export async function updateAdminUser(
  id: string,
  payload: { full_name?: string; role?: AppRole; password?: string }
): Promise<AdminUserRow> {
  const res = await fetch(`${getBackendUrl()}/admin/users/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: headersJson(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await parseDetail(res));
  return res.json() as Promise<AdminUserRow>;
}

export async function deleteAdminUser(id: string): Promise<void> {
  const res = await fetch(`${getBackendUrl()}/admin/users/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: headersJson(),
  });
  if (!res.ok) throw new Error(await parseDetail(res));
}
