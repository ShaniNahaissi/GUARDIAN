import React, { useEffect, useState } from 'react';
import { Card } from '../components/atoms/Card';
import { Button } from '../components/atoms/Button';
import { ArrowLeft, Camera } from 'lucide-react';
import { getCameras, updateCamera } from '../services/dataService';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

interface EditCameraPageProps {
  cameraId: string;
  onBack: () => void;
}

export const EditCameraPage: React.FC<EditCameraPageProps> = ({ cameraId, onBack }) => {
  const { canWriteCameras } = useAuth();
  const [serverName, setServerName] = useState('');
  const [location, setLocation] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    if (!canWriteCameras) {
      showToast('You do not have permission to edit servers.', 'error');
      onBack();
      return;
    }

    let isMounted = true;
    (async () => {
      try {
        const cameras = await getCameras();
        const target = cameras.find(c => c.id === cameraId);
        if (isMounted) {
          if (target) {
            setServerName(target.name);
            setLocation(target.location || '');
            setImageUrl(target.imageUrl || '');
          } else {
            showToast('Camera not found', 'error');
            onBack();
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          showToast('Failed to load camera details.', 'error');
          onBack();
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [cameraId, canWriteCameras, onBack, showToast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await updateCamera(cameraId, {
      name: serverName.trim(),
      location: location.trim(),
      imageUrl: imageUrl.trim() || undefined,
    });
    if (success) {
      showToast('Camera updated successfully!', 'success');
      onBack();
    } else {
      showToast('Failed to update camera.', 'error');
    }
  };

  if (!canWriteCameras || isLoading) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 sm:items-center sm:gap-4 mb-6">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold mb-1">Edit Camera</h2>
          <p className="text-guardian-muted text-sm">Modify existing camera properties</p>
        </div>
      </div>

      <Card className="p-4 sm:p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6 border-b border-gray-800 pb-4">
          <Camera className="w-8 h-8 text-guardian-accent" />
          <h3 className="text-lg font-bold">Edit Settings</h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Camera ID / Stream UUID</label>
            <input 
              type="text" 
              value={cameraId}
              disabled
              className="w-full bg-gray-900/50 border border-gray-800 rounded-lg px-4 py-2 text-gray-500 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Camera Name</label>
            <input 
              type="text" 
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Location</label>
            <input 
              type="text" 
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Image URL (Optional placeholder)</label>
            <input 
              type="text" 
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
            />
          </div>

          <div className="pt-4 flex flex-col sm:flex-row sm:justify-end gap-3">
            <Button className="w-full sm:w-auto" variant="secondary" type="button" onClick={onBack}>Cancel</Button>
            <Button className="w-full sm:w-auto" type="submit">Save Changes</Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
