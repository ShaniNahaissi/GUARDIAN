import React from 'react';
import { Card } from '../atoms/Card';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { Eye, Bell, Edit2, Trash2 } from 'lucide-react';
import { LiveStreamPreview } from './LiveStreamPreview';
import { useToast } from '../../context/ToastContext';

interface CameraFeedCardProps {
  id: string;
  name: string;
  location: string;
  status: 'normal' | 'warning' | 'major' | 'critical';
  statusText: string;
  imageUrl: string;
  time: string;
  canWrite?: boolean;
  onView: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export const CameraFeedCard: React.FC<CameraFeedCardProps> = ({ 
  id, name, location, status, statusText, imageUrl, time, canWrite, onView, onEdit, onDelete 
}) => {
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
          {!imageUrl.trim() ? (
            <LiveStreamPreview streamId={id} className="opacity-90 group-hover:opacity-100 transition-opacity" />
          ) : (
            <img src={imageUrl} alt={name} className="object-cover w-full h-full opacity-80 group-hover:opacity-100 transition-opacity" />
          )}
        </div>
        
        <div className="absolute top-3 left-3">
          <Badge status={status}>{statusText}</Badge>
        </div>
        <div className="absolute top-3 right-3 bg-black/60 px-2 py-1 rounded text-xs font-mono">
          {time}
        </div>
      </div>
      
      <div className="p-4 flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-end bg-guardian-card">
        <div className="min-w-0">
          <h3 className="font-bold text-lg leading-tight">{name}</h3>
          <p className="text-sm text-guardian-muted mt-1">{location}</p>
          <p className="text-xs text-gray-500 mt-2">{id}</p>
        </div>
        
        <div className="flex w-full sm:w-auto gap-2">
          <Button variant="secondary" className="flex-1 sm:flex-none !px-3 !py-1.5 text-xs" onClick={() => onView(id)}>
            <Eye className="w-4 h-4" /> View
          </Button>
          <Button variant={status === 'normal' ? 'secondary' : 'danger'} className="flex-1 sm:flex-none !px-3 !py-1.5 text-xs" onClick={handleAlert}>
            <Bell className="w-4 h-4" /> Alert
          </Button>
          {canWrite && (
            <>
              <Button variant="secondary" className="flex-none !px-3 !py-1.5 text-xs" onClick={() => onEdit?.(id)} title="Edit Camera">
                <Edit2 className="w-4 h-4" />
              </Button>
              <Button variant="danger" className="flex-none !px-3 !py-1.5 text-xs" onClick={() => onDelete?.(id)} title="Delete Camera">
                <Trash2 className="w-4 h-4" />
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
};
