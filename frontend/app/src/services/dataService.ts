import {
  coerceDevLoopbackBackendToProxy,
  getBackendUrl,
  isBackendEnabled,
  upgradeLocalHttpBackendUrl,
} from './apiBase';
import { getStoredAccessToken } from './authApi';

export interface CameraInfo {
  id: string;
  name: string;
  location: string;
  status: 'normal' | 'warning' | 'major' | 'critical';
  statusText: string;
  imageUrl: string;
  time: string;
}

export interface SystemStats {
  activeCameras: number;
  activeOnline: number;
  warningAlerts: number;
  majorAlerts: number;
  criticalAlerts: number;
}

// Mock Data — statuses are neutral; weapon alerts come only from live inference when using backend streams.
const MOCK_CAMERAS: CameraInfo[] = [
  { id: "CAM-001", name: "Main Entrance - Parking", location: "Building A - North Wing", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1542204165-65bf26472b9b?auto=format&fit=crop&q=80&w=600", time: "23:47:15" },
  { id: "CAM-007", name: "Hallway - 3rd Floor", location: "Building A - East Wing", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1541888047466-d7488abfc0ce?auto=format&fit=crop&q=80&w=600", time: "23:45:32" },
  { id: "CAM-002", name: "Main Lobby", location: "Building A - Ground Floor", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600", time: "23:42:18" },
  { id: "CAM-003", name: "Warehouse - Section B", location: "Building C - Storage", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1586528116311-ad8ed7c1590a?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
  { id: "CAM-004", name: "Loading Dock", location: "Building C - Rear", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
  { id: "CAM-005", name: "Cafeteria", location: "Building B - 2nd Floor", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
];

const MOCK_STATS: SystemStats = {
  activeCameras: 6,
  activeOnline: 6,
  warningAlerts: 0,
  majorAlerts: 0,
  criticalAlerts: 0,
};

const apiAuthHeaders = (): Record<string, string> => {
  const h: Record<string, string> = {};
  const t = getStoredAccessToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
};

export { coerceDevLoopbackBackendToProxy, getBackendUrl, isBackendEnabled, upgradeLocalHttpBackendUrl };

export interface StreamTrackPayload {
  stream_id: string;
  frame_seq: number;
  tracks: Array<{
    track_id: number;
    bbox: [number, number, number, number];
    class_name: string;
    confidence: number;
  }>;
}

/**
 * Scheme + host + port for stream endpoints (not under /api).
 * Backend: WS /producer/{id} (ingest JPEG), WS /consumer/{id} (binary JPEG + JSON tracks), GET /consumer/{id}/frame (snapshot).
 */
const getBackendOriginForStreams = (): string => {
  const backendUrl = getBackendUrl();
  if (backendUrl.startsWith('/')) {
    return typeof window !== 'undefined' ? window.location.origin : '';
  }
  try {
    return new URL(backendUrl).origin;
  } catch {
    const stripped = backendUrl.replace(/\/?api\/?$/i, '').replace(/\/$/, '');
    return stripped;
  }
};

/** Single path segment for /producer and /consumer paths (FastAPI decodes once). */
const encodeStreamIdForPath = (streamId: string): string =>
  encodeURIComponent(streamId.trim());

const streamWsUrl = (pathPrefix: 'producer' | 'consumer', streamId: string, originOverride?: string): string => {
  const id = encodeStreamIdForPath(streamId);
  const origin = originOverride?.trim() || getBackendOriginForStreams();
  const base = origin || (typeof window !== 'undefined' ? window.location.origin : '');
  const httpUrl = new URL(base.startsWith('http') ? base : `https://${base}`);
  const wsProtocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProtocol}//${httpUrl.host}/${pathPrefix}/${id}`;
};

/** WebSocket: send binary JPEG frames to the backend producer. */
export const getProducerWebSocketUrl = (streamId: string): string =>
  streamWsUrl('producer', streamId);

/**
 * WebSocket: receive processed JPEG (binary) then JSON {@link StreamTrackPayload} per frame.
 * Connect from the same origin as stream routes (Vite proxies /consumer with WS upgrade).
 */
export const getConsumerWebSocketUrl = (streamId: string): string =>
  streamWsUrl('consumer', streamId);

/** @deprecated Use {@link getProducerWebSocketUrl}. */
export const getCameraStreamWebSocketUrl = getProducerWebSocketUrl;

/** Single JPEG snapshot: backend GET /consumer/{stream_id}/frame */
export const getConsumerSnapshotUrl = (streamId: string): string => {
  const origin = getBackendOriginForStreams();
  const id = encodeStreamIdForPath(streamId);
  return `${origin}/consumer/${id}/frame`;
};

/** Consumer WebSocket URL against an explicit backend origin (custom server). */
export const getConsumerWebSocketUrlForBase = (backendOriginInput: string, streamId: string): string => {
  const origin = normalizeConsumeBackendOrigin(backendOriginInput);
  const base = origin || getBackendOriginForStreams();
  return streamWsUrl('consumer', streamId, base);
};

/** Normalize user input: host:port, http(s)://host, or URL ending with /api → origin only. */
export const normalizeConsumeBackendOrigin = (input: string): string => {
  const trimmed = input.trim();
  if (!trimmed) return '';
  let s = trimmed;
  if (s.startsWith('/')) {
    return typeof window !== 'undefined' ? window.location.origin : '';
  }
  if (!/^https?:\/\//i.test(s)) {
    s = `https://${s}`;
  }
  try {
    const u = new URL(s);
    return u.origin;
  } catch {
    return '';
  }
};

/** Latest detection counts from backend stream store (poll when backend enabled). */
export async function fetchStreamMeta(
  streamId: string,
): Promise<{ count: number; max_score: number; weapon_count: number; confirmed_threat: boolean } | null> {
  if (!isBackendEnabled()) return null;
  const id = encodeURIComponent(streamId.trim());
  if (!id) return null;
  try {
    const res = await fetch(`${getBackendUrl()}/streams/${id}/meta`, { headers: apiAuthHeaders() });
    if (!res.ok) return null;
    return (await res.json()) as { count: number; max_score: number; weapon_count: number; confirmed_threat: boolean };
  } catch {
    return null;
  }
}

export type AddCameraPayload = Partial<CameraInfo> & {
  streamUuid?: string;
  /** Host or full URL of the backend that serves WebSocket /consumer/{uuid}. Empty → use Settings backend. */
  consumerBackendBase?: string;
};

export const getCameras = async (): Promise<CameraInfo[]> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras`, { headers: apiAuthHeaders() });
      if (!res.ok) throw new Error('Failed to fetch');
      return await res.json();
    } catch (e) {
      console.error('Backend fetch failed, returning empty cameras list.', e);
      return [];
    }
  }
  return Promise.resolve(MOCK_CAMERAS);
};

export const getSystemStats = async (): Promise<SystemStats> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/stats`, { headers: apiAuthHeaders() });
      if (!res.ok) throw new Error('Failed to fetch');
      return await res.json();
    } catch (e) {
      console.error('Backend fetch failed, returning zero stats.', e);
      return {
        activeCameras: 0,
        activeOnline: 0,
        warningAlerts: 0,
        majorAlerts: 0,
        criticalAlerts: 0
      };
    }
  }
  return Promise.resolve(MOCK_STATS);
};

export const addCamera = async (cameraData: AddCameraPayload): Promise<boolean> => {
  const streamUuid = (cameraData.streamUuid || '').trim();
  const customBase = (cameraData.consumerBackendBase || '').trim();
  const consumeOrigin = customBase ? normalizeConsumeBackendOrigin(customBase) : '';
  if (customBase && !consumeOrigin) {
    console.error('Invalid backend server for consume URL');
    return false;
  }
  const explicitImage = (cameraData.imageUrl ?? '').trim();
  const location =
    cameraData.location ??
    (consumeOrigin ? `${consumeOrigin} · ${streamUuid}` : streamUuid);
  const body = {
    name: cameraData.name ?? '',
    location,
    imageUrl: explicitImage || undefined,
    streamUuid: streamUuid || undefined,
  };

  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...apiAuthHeaders(),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to add camera');
      return true;
    } catch (e) {
      console.error('Backend add camera failed', e);
      return false;
    }
  }

  // Mock adding a camera
  const id = streamUuid || `CAM-${String(MOCK_CAMERAS.length + 1).padStart(3, '0')}`;
  const newCamera: CameraInfo = {
    id,
    name: cameraData.name || 'New Server',
    location,
    status: 'normal',
    statusText: 'NORMAL',
    imageUrl:
      explicitImage ||
      (streamUuid ? '' : 'https://images.unsplash.com/photo-1542204165-65bf26472b9b?auto=format&fit=crop&q=80&w=600'),
    time: new Date().toLocaleTimeString(),
  };
  MOCK_CAMERAS.push(newCamera);
  return true;
};

export const updateCamera = async (id: string, payload: Partial<CameraInfo>): Promise<boolean> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...apiAuthHeaders(),
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Failed to update camera');
      return true;
    } catch (e) {
      console.error('Backend update camera failed', e);
      return false;
    }
  }

  // Mock
  const idx = MOCK_CAMERAS.findIndex((c) => c.id === id);
  if (idx !== -1) {
    MOCK_CAMERAS[idx] = { ...MOCK_CAMERAS[idx], ...payload };
    return true;
  }
  return false;
};

export const deleteCamera = async (id: string): Promise<boolean> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: apiAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to delete camera');
      return true;
    } catch (e) {
      console.error('Backend delete camera failed', e);
      return false;
    }
  }

  // Mock
  const idx = MOCK_CAMERAS.findIndex((c) => c.id === id);
  if (idx !== -1) {
    MOCK_CAMERAS.splice(idx, 1);
    return true;
  }
  return false;
};
