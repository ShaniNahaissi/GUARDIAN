import React, { useState, useEffect } from 'react';
import { StatCard } from '../components/molecules/StatCard';
import { CameraFeedCard } from '../components/molecules/CameraFeedCard';
import { Button } from '../components/atoms/Button';
import { Filter, RefreshCcw, Plus } from 'lucide-react';
import { getCameras, getSystemStats } from '../services/dataService';
import type { CameraInfo, SystemStats } from '../services/dataService';

interface DashboardProps {
  onViewCamera: (id: string) => void;
  onAddCamera: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onViewCamera, onAddCamera }) => {
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
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

  // Derive unique statusText labels from loaded cameras
  const availableLabels = Array.from(new Set(cameras.map(c => c.statusText)));

  const filteredCameras = cameras.filter(c => filter === 'all' || c.statusText === filter);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Active Cameras" value={stats?.activeCameras.toString() || '0'} subValue={`${stats?.activeOnline || 0} Online`} trend="+2" iconType="camera" statusLabel="All Online" statusBadge="normal" />
        <StatCard title="Warning Alerts" value={stats?.warningAlerts.toString() || '0'} subValue="Priority" trend="-2 from yesterday" iconType="warning" statusLabel="Low Risk" statusBadge="warning" />
        <StatCard title="Major Alerts" value={stats?.majorAlerts.toString() || '0'} subValue="Priority" trend="+1 from yesterday" iconType="major" statusLabel="Medium Risk" statusBadge="major" />
        <StatCard title="Critical Alerts" value={stats?.criticalAlerts.toString() || '0'} subValue="Priority" trend="Requires action" iconType="critical" statusLabel="High Risk" statusBadge="critical" />
      </div>

      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold mb-1">Live Camera Feeds</h2>
          <p className="text-guardian-muted text-sm">Real-time weapon detection monitoring</p>
        </div>
        <div className="flex gap-3 relative">
          <div>
            <Button variant="secondary" onClick={() => setShowFilterMenu(!showFilterMenu)}>
              <Filter className="w-4 h-4" /> Filter {filter !== 'all' && `(${filter})`}
            </Button>
            {showFilterMenu && (
              <div className="absolute top-full mt-2 left-0 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20 overflow-hidden">
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
          <Button variant="secondary" onClick={loadData}><RefreshCcw className="w-4 h-4" /> Refresh</Button>
          <Button variant="primary" onClick={onAddCamera}><Plus className="w-4 h-4" /> Add Camera</Button>
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
            onView={onViewCamera}
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
