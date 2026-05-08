import React from 'react';
import { Card } from '../atoms/Card';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Eye, Bell } from 'lucide-react';

interface CameraFeedCardProps {
  id: string;
  name: string;
  location: string;
  status: 'normal' | 'warning' | 'major' | 'critical';
  statusText: string;
  imageUrl: string;
  time: string;
  onView: (id: string) => void;
}

import { useToast } from '../../context/ToastContext';

export const CameraFeedCard: React.FC<CameraFeedCardProps> = ({ id, name, location, status, statusText, imageUrl, time, onView }) => {
  const { showToast } = useToast();

  const handleAlert = () => {
    // Stub for backend command
    console.log(`Sending alert for camera ${id} to backend...`);
    showToast(`Alert sent for ${name}!`);
  };

  return (
    <Card className="flex flex-col group">
      <div className="relative h-48 bg-gray-900 overflow-hidden">
        {/* Placeholder for camera feed image */}
        <div className="absolute inset-0 bg-gray-800 flex items-center justify-center text-guardian-muted">
          <img src={imageUrl} alt={name} className="object-cover w-full h-full opacity-80 group-hover:opacity-100 transition-opacity" />
        </div>
        
        <div className="absolute top-3 left-3">
          <Badge status={status}>{statusText}</Badge>
        </div>
        <div className="absolute top-3 right-3 bg-black/60 px-2 py-1 rounded text-xs font-mono">
          {time}
        </div>
      </div>
      
      <div className="p-4 flex justify-between items-end bg-guardian-card">
        <div>
          <h3 className="font-bold text-lg leading-tight">{name}</h3>
          <p className="text-sm text-guardian-muted mt-1">{location}</p>
          <p className="text-xs text-gray-500 mt-2">{id}</p>
        </div>
        
        <div className="flex gap-2">
          <Button variant="secondary" className="!px-3 !py-1.5 text-xs" onClick={() => onView(id)}>
            <Eye className="w-4 h-4" /> View
          </Button>
          <Button variant={status === 'normal' ? 'secondary' : 'danger'} className="!px-3 !py-1.5 text-xs" onClick={handleAlert}>
            <Bell className="w-4 h-4" /> Alert
          </Button>
        </div>
      </div>
    </Card>
  );
};
