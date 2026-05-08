import React, { useState } from 'react';
import { Card } from '../components/atoms/Card';
import { Button } from '../components/atoms/Button';

export const SettingsPage: React.FC = () => {
  const [useBackend, setUseBackend] = useState(() => {
    const saved = localStorage.getItem('guardian_use_backend');
    return saved !== 'false'; // Default to true
  });
  
  const [backendUrl, setBackendUrl] = useState(() => {
    const savedUrl = localStorage.getItem('guardian_backend_url');
    return savedUrl || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/api';
  });

  const handleSave = () => {
    localStorage.setItem('guardian_use_backend', useBackend.toString());
    localStorage.setItem('guardian_backend_url', backendUrl);
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-1">Settings</h2>
        <p className="text-guardian-muted text-sm">Configure application settings</p>
      </div>

      <Card className="p-6 max-w-2xl space-y-6">
        <h3 className="text-lg font-bold mb-4">Data Source Configuration</h3>
        
        <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
          <div>
            <p className="font-medium text-white">Use Backend API</p>
            <p className="text-sm text-guardian-muted mt-1">
              Toggle between mock data (for dev) and real backend API.
            </p>
          </div>
          
          <label className="relative inline-flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              className="sr-only peer" 
              checked={useBackend}
              onChange={(e) => setUseBackend(e.target.checked)}
            />
            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-guardian-accent"></div>
          </label>
        </div>

        {useBackend && (
          <div className="p-4 bg-gray-900 rounded-lg">
            <label className="block font-medium text-white mb-2">Backend URL</label>
            <input 
              type="text" 
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              placeholder="http://localhost:8000/api"
            />
            <p className="text-xs text-guardian-muted mt-2">
              Default is taken from .env file (VITE_BACKEND_URL)
            </p>
          </div>
        )}

        <div className="pt-4 border-t border-gray-800 flex justify-end">
          <Button onClick={handleSave}>
            Save & Refresh
          </Button>
        </div>
      </Card>
    </div>
  );
};
