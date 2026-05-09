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

// Mock Data
const MOCK_CAMERAS: CameraInfo[] = [
  { id: "CAM-001", name: "Main Entrance - Parking", location: "Building A - North Wing", status: "critical", statusText: "WEAPON DETECTED", imageUrl: "https://images.unsplash.com/photo-1542204165-65bf26472b9b?auto=format&fit=crop&q=80&w=600", time: "23:47:15" },
  { id: "CAM-007", name: "Hallway - 3rd Floor", location: "Building A - East Wing", status: "major", statusText: "Suspicious Object", imageUrl: "https://images.unsplash.com/photo-1541888047466-d7488abfc0ce?auto=format&fit=crop&q=80&w=600", time: "23:45:32" },
  { id: "CAM-002", name: "Main Lobby", location: "Building A - Ground Floor", status: "warning", statusText: "Unidentified Item", imageUrl: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600", time: "23:42:18" },
  { id: "CAM-003", name: "Warehouse - Section B", location: "Building C - Storage", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1586528116311-ad8ed7c1590a?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
  { id: "CAM-004", name: "Loading Dock", location: "Building C - Rear", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
  { id: "CAM-005", name: "Cafeteria", location: "Building B - 2nd Floor", status: "normal", statusText: "NORMAL", imageUrl: "https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&q=80&w=600", time: "23:47:20" },
];

const MOCK_STATS: SystemStats = {
  activeCameras: 24,
  activeOnline: 24,
  warningAlerts: 5,
  majorAlerts: 2,
  criticalAlerts: 1
};

const isBackendEnabled = () => {
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

const getBackendUrl = () => {
  const fromStorage = localStorage.getItem('guardian_backend_url');
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

/**
 * Scheme + host + port for stream endpoints (not under /api).
 * Backend: GET /consumer/{stream_id} (MJPEG), GET /consumer/{stream_id}/frame (JPEG), WS /sw/stream/{stream_id}.
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

/** Single path segment for /consumer/{stream_id} and /sw/stream/{stream_id} (FastAPI decodes once). */
const encodeConsumerStreamIdForPath = (streamId: string): string =>
  encodeURIComponent(streamId.trim());

export const getCameraStreamWebSocketUrl = (uuid: string): string => {
  const safeUuid = encodeConsumerStreamIdForPath(uuid);
  const origin = getBackendOriginForStreams();
  const httpUrl = new URL(origin);
  const wsProtocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProtocol}//${httpUrl.host}/sw/stream/${safeUuid}`;
};

/** MJPEG multipart stream: same contract as backend GET /consumer/{stream_id}. */
export const getConsumerMjpegUrl = (streamId: string): string => {
  const origin = getBackendOriginForStreams();
  const id = encodeConsumerStreamIdForPath(streamId);
  return `${origin}/consumer/${id}`;
};

/** Single JPEG frame: backend GET /consumer/{stream_id}/frame */
export const getConsumerSnapshotUrl = (streamId: string): string => {
  const origin = getBackendOriginForStreams();
  const id = encodeConsumerStreamIdForPath(streamId);
  return `${origin}/consumer/${id}/frame`;
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

export const getConsumerMjpegUrlForBase = (backendOriginInput: string, streamId: string): string => {
  const origin = normalizeConsumeBackendOrigin(backendOriginInput);
  const base = origin || getBackendOriginForStreams();
  const id = encodeConsumerStreamIdForPath(streamId);
  return `${base}/consumer/${id}`;
};

export type AddCameraPayload = Partial<CameraInfo> & {
  streamUuid?: string;
  /** Host or full URL of the backend that serves GET /consumer/{uuid}. Empty → use Settings backend. */
  consumerBackendBase?: string;
};

export const getCameras = async (): Promise<CameraInfo[]> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras`);
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
      const res = await fetch(`${getBackendUrl()}/stats`);
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
  const imageUrl =
    cameraData.imageUrl?.trim() ||
    (streamUuid
      ? customBase
        ? getConsumerMjpegUrlForBase(customBase, streamUuid)
        : getConsumerMjpegUrl(streamUuid)
      : '');
  const location =
    cameraData.location ??
    (consumeOrigin ? `${consumeOrigin} · ${streamUuid}` : streamUuid);
  const body = {
    name: cameraData.name ?? '',
    location,
    imageUrl: imageUrl || undefined,
    streamUuid: streamUuid || undefined,
  };

  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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
    imageUrl: imageUrl || getConsumerMjpegUrl(id),
    time: new Date().toLocaleTimeString(),
  };
  MOCK_CAMERAS.push(newCamera);
  return true;
};
