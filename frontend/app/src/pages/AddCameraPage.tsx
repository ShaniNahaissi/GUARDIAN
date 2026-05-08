import React, { useState } from 'react';
import { Card } from '../components/atoms/Card';
import { Button } from '../components/atoms/Button';
import { ArrowLeft, Camera } from 'lucide-react';
import { addCamera } from '../services/dataService';
import { useToast } from '../context/ToastContext';

interface AddCameraPageProps {
  onBack: () => void;
}

export const AddCameraPage: React.FC<AddCameraPageProps> = ({ onBack }) => {
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await addCamera({ name, location, imageUrl });
    if (success) {
      showToast('Camera added successfully!', 'success');
      onBack();
    } else {
      showToast('Failed to add camera.', 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h2 className="text-2xl font-bold mb-1">Add New Camera</h2>
          <p className="text-guardian-muted text-sm">Register a new camera to the system</p>
        </div>
      </div>

      <Card className="p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6 border-b border-gray-800 pb-4">
          <Camera className="w-8 h-8 text-guardian-accent" />
          <h3 className="text-lg font-bold">Camera Details</h3>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Camera Name</label>
            <input 
              type="text" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
              placeholder="e.g. Main Entrance - Parking"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Location</label>
            <input 
              type="text" 
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
              placeholder="e.g. Building A - North Wing"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Stream / Image URL (Optional)</label>
            <input 
              type="text" 
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              placeholder="https://..."
            />
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <Button variant="secondary" type="button" onClick={onBack}>Cancel</Button>
            <Button type="submit">Save Camera</Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
