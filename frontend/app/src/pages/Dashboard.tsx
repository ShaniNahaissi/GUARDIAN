import React, { useState, useEffect, useMemo } from 'react';
import { StatCard } from '../components/molecules/StatCard';
import { CameraFeedCard } from '../components/molecules/CameraFeedCard';
import { Button } from '../components/atoms/Button';
import { Filter, RefreshCcw, Plus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getCameras, getSystemStats, deleteCamera, fetchStreamMeta, isBackendEnabled } from '../services/dataService';
import type { CameraInfo, SystemStats } from '../services/dataService';
import { useToast } from '../context/ToastContext';

interface DashboardProps {
  onViewCamera: (id: string) => void;
  onAddCamera: () => void;
  onEditCamera?: (id: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onViewCamera, onAddCamera, onEditCamera }) => {
  const { canWriteCameras } = useAuth();
  const { showToast } = useToast();
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [liveThreatByStream, setLiveThreatByStream] = useState<Record<string, boolean | undefined>>({});
  const [filter, setFilter] = useState<string>('all');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const loadData = async () => {
    try {
      const [camerasData, statsData] = await Promise.all([
        getCameras(),
        getSystemStats()
      ]);
      setCameras(camerasData);
      setStats(statsData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!isBackendEnabled() || cameras.length === 0) {
      setLiveThreatByStream({});
      return;
    }
    let cancelled = false;
    const poll = async () => {
      const next: Record<string, boolean | undefined> = {};
      await Promise.all(
        cameras.map(async (c) => {
          const meta = await fetchStreamMeta(c.id);
          next[c.id] = meta === null ? undefined : meta.count > 0;
        }),
      );
      if (!cancelled) setLiveThreatByStream(next);
    };
    void poll();
    const timer = window.setInterval(poll, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [cameras]);

  const displayCameras = useMemo(() => {
    return cameras.map((c) => {
      const t = liveThreatByStream[c.id];
      if (t === undefined) return c;
      if (t) return { ...c, status: 'critical' as const, statusText: 'WEAPON DETECTED' };
      return { ...c, status: 'normal' as const, statusText: 'NORMAL' };
    });
  }, [cameras, liveThreatByStream]);

  const displayStats = useMemo(() => {
    if (!stats) return null;
    if (!isBackendEnabled()) return stats;
    const liveCritical = cameras.filter((c) => liveThreatByStream[c.id] === true).length;
    return { ...stats, criticalAlerts: liveCritical };
  }, [stats, cameras, liveThreatByStream]);

  const handleDeleteCamera = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this camera? This action cannot be undone.")) {
      const success = await deleteCamera(id);
      if (success) {
        showToast("Camera deleted successfully.", "success");
        loadData();
      } else {
        showToast("Failed to delete camera.", "error");
      }
    }
  };

  // Derive unique statusText labels from loaded cameras
  const availableLabels = Array.from(new Set(displayCameras.map((c) => c.statusText)));

  const filteredCameras = displayCameras.filter((c) => filter === 'all' || c.statusText === filter);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Active Cameras" value={displayStats?.activeCameras.toString() || '0'} subValue={`${displayStats?.activeOnline || 0} Online`} trend="+2" iconType="camera" statusLabel="All Online" statusBadge="normal" />
        <StatCard title="Warning Alerts" value={displayStats?.warningAlerts.toString() || '0'} subValue="Priority" trend="-2 from yesterday" iconType="warning" statusLabel="Low Risk" statusBadge="warning" />
        <StatCard title="Major Alerts" value={displayStats?.majorAlerts.toString() || '0'} subValue="Priority" trend="+1 from yesterday" iconType="major" statusLabel="Medium Risk" statusBadge="major" />
        <StatCard title="Critical Alerts" value={displayStats?.criticalAlerts.toString() || '0'} subValue="Priority" trend="Requires action" iconType="critical" statusLabel="High Risk" statusBadge="critical" />
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-end">
        <div>
          <h2 className="text-2xl font-bold mb-1">Live Camera Feeds</h2>
          <p className="text-guardian-muted text-sm">Real-time weapon detection monitoring</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 relative w-full sm:w-auto">
          <div className="relative w-full sm:w-auto">
            <Button className="w-full sm:w-auto" variant="secondary" onClick={() => setShowFilterMenu(!showFilterMenu)}>
              <Filter className="w-4 h-4" /> Filter {filter !== 'all' && `(${filter})`}
            </Button>
            {showFilterMenu && (
              <div className="absolute top-full mt-2 left-0 w-full sm:w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20 overflow-hidden">
                <button
                  className={`w-full text-left px-4 py-2 hover:bg-gray-700 ${filter === 'all' ? 'text-guardian-accent' : ''}`}
                  onClick={() => { setFilter('all'); setShowFilterMenu(false); }}
                >
                  All
                </button>
                {availableLabels.map(label => (
                  <button
                    key={label}
                    className={`w-full text-left px-4 py-2 hover:bg-gray-700 ${filter === label ? 'text-guardian-accent' : ''}`}
                    onClick={() => { setFilter(label); setShowFilterMenu(false); }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button className="w-full sm:w-auto" variant="secondary" onClick={loadData}><RefreshCcw className="w-4 h-4" /> Refresh</Button>
          {canWriteCameras && (
            <Button className="w-full sm:w-auto" variant="primary" onClick={onAddCamera}><Plus className="w-4 h-4" /> Add server</Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCameras.map((camera) => (
          <CameraFeedCard 
            key={camera.id}
            id={camera.id}
            name={camera.name}
            location={camera.location}
            status={camera.status}
            statusText={camera.statusText}
            imageUrl={camera.imageUrl}
            time={camera.time}
            canWrite={canWriteCameras}
            onView={onViewCamera}
            onEdit={onEditCamera}
            onDelete={handleDeleteCamera}
          />
        ))}
        {filteredCameras.length === 0 && (
          <div className="col-span-full py-12 text-center text-guardian-muted">
            No cameras match the current filter.
          </div>
        )}
      </div>
    </div>
  );
};
