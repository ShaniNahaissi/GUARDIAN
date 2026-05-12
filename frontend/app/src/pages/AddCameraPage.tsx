import React, { useEffect, useState } from 'react';
import { Card } from '../components/atoms/Card';
import { Button } from '../components/atoms/Button';
import { ArrowLeft, Camera } from 'lucide-react';
import { addCamera } from '../services/dataService';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

interface AddCameraPageProps {
  onBack: () => void;
}

export const AddCameraPage: React.FC<AddCameraPageProps> = ({ onBack }) => {
  const { canWriteCameras } = useAuth();
  const [serverName, setServerName] = useState('');
  const [consumerBackendBase, setConsumerBackendBase] = useState('');
  const [streamUuid, setStreamUuid] = useState('');
  const { showToast } = useToast();

  useEffect(() => {
    if (!canWriteCameras) {
      showToast('You do not have permission to add servers.', 'error');
      onBack();
    }
  }, [canWriteCameras, onBack, showToast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await addCamera({
      name: serverName.trim(),
      streamUuid: streamUuid.trim(),
      consumerBackendBase: consumerBackendBase.trim(),
    });
    if (success) {
      showToast('Server added successfully!', 'success');
      onBack();
    } else {
      showToast('Failed to add server.', 'error');
    }
  };

  if (!canWriteCameras) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 sm:items-center sm:gap-4 mb-6">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold mb-1">Add server</h2>
          <p className="text-guardian-muted text-sm">Display name plus where to consume the stream</p>
        </div>
      </div>

      <Card className="p-4 sm:p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6 border-b border-gray-800 pb-4">
          <Camera className="w-8 h-8 text-guardian-accent" />
          <h3 className="text-lg font-bold">Server</h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Server name</label>
            <input 
              type="text" 
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
              placeholder="e.g. Main entrance edge"
            />
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-900/40 p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-white mb-1">Live stream (same backend as API)</label>
              <p className="text-xs text-guardian-muted mb-3">
                Use the same <strong>stream UUID</strong> as on the Camera Stream page. The dashboard opens{' '}
                <code className="text-guardian-accent">WS /consumer/&lt;uuid&gt;</code> (not under{' '}
                <code className="text-guardian-muted">/api</code>). Optional backend host below if it differs from Settings.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-guardian-muted mb-1">Backend server (optional)</label>
              <input
                type="text"
                value={consumerBackendBase}
                onChange={(e) => setConsumerBackendBase(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
                placeholder="e.g. 192.168.0.10:8000 (defaults to https) or http://legacy-host:8000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-guardian-muted mb-1">Stream UUID</label>
              <input 
                type="text" 
                value={streamUuid}
                onChange={(e) => setStreamUuid(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
                required 
                placeholder="Same id as WS /producer/{uuid} and WS /consumer/{uuid}"
              />
            </div>
          </div>

          <div className="pt-4 flex flex-col sm:flex-row sm:justify-end gap-3">
            <Button className="w-full sm:w-auto" variant="secondary" type="button" onClick={onBack}>Cancel</Button>
            <Button className="w-full sm:w-auto" type="submit">Save server</Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
