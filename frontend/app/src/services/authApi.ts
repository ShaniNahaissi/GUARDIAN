import { getBackendUrl } from './apiBase';

export const GUARDIAN_ACCESS_TOKEN_KEY = 'guardian_access_token';

export type AppRole = 'admin' | 'operator' | 'viewer';

export interface AuthUser {
  id: string;
  username: string;
  fullName: string;
  role: AppRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export const getStoredAccessToken = (): string | null =>
  typeof localStorage === 'undefined' ? null : localStorage.getItem(GUARDIAN_ACCESS_TOKEN_KEY);

export const setStoredAccessToken = (token: string | null): void => {
  if (typeof localStorage === 'undefined') return;
  if (token) localStorage.setItem(GUARDIAN_ACCESS_TOKEN_KEY, token);
  else localStorage.removeItem(GUARDIAN_ACCESS_TOKEN_KEY);
};

const authJsonHeaders = (): HeadersInit => ({
  'Content-Type': 'application/json',
});

const bearerHeaders = (token: string): HeadersInit => ({
  Authorization: `Bearer ${token}`,
});

export async function loginRequest(username: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${getBackendUrl()}/auth/login`, {
    method: 'POST',
    headers: authJsonHeaders(),
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = typeof err?.detail === 'string' ? err.detail : 'Login failed';
    throw new Error(detail);
  }
  return res.json() as Promise<TokenResponse>;
}

export async function registerRequest(
  username: string,
  password: string,
  full_name: string
): Promise<TokenResponse> {
  const res = await fetch(`${getBackendUrl()}/auth/register`, {
    method: 'POST',
    headers: authJsonHeaders(),
    body: JSON.stringify({ username, password, full_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = typeof err?.detail === 'string' ? err.detail : 'Registration failed';
    throw new Error(detail);
  }
  return res.json() as Promise<TokenResponse>;
}

export async function fetchMe(token: string): Promise<AuthUser> {
  const res = await fetch(`${getBackendUrl()}/auth/me`, {
    headers: bearerHeaders(token),
  });
  if (!res.ok) throw new Error('Session expired');
  return res.json() as Promise<AuthUser>;
}

export function roleCanWriteCameras(_role: string): boolean {
  // ponytail: every role now has full self-service camera permissions (backend/bl/rbac.py);
  // only /api/admin/* (managing other users) stays admin-only.
  return true;
}
