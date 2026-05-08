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

const getBackendUrl = () => {
  return localStorage.getItem('guardian_backend_url') || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/api';
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

export const addCamera = async (cameraData: Partial<CameraInfo>): Promise<boolean> => {
  if (isBackendEnabled()) {
    try {
      const res = await fetch(`${getBackendUrl()}/cameras`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cameraData),
      });
      if (!res.ok) throw new Error('Failed to add camera');
      return true;
    } catch (e) {
      console.error('Backend add camera failed', e);
      return false;
    }
  }
  
  // Mock adding a camera
  const newCamera: CameraInfo = {
    id: `CAM-00${MOCK_CAMERAS.length + 1}`,
    name: cameraData.name || 'New Camera',
    location: cameraData.location || 'Unknown Location',
    status: 'normal',
    statusText: 'NORMAL',
    imageUrl: cameraData.imageUrl || 'https://images.unsplash.com/photo-1542204165-65bf26472b9b?auto=format&fit=crop&q=80&w=600',
    time: new Date().toLocaleTimeString(),
  };
  MOCK_CAMERAS.push(newCamera);
  return true;
};
