import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface AlertBannerProps {
  title: string;
  description: string;
  onClose: () => void;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ title, description, onClose }) => {
  return (
    <div className="bg-guardian-danger text-white rounded-xl p-4 flex items-center justify-between shadow-lg shadow-red-500/20 mb-6">
      <div className="flex items-center gap-4">
        <div className="bg-white/20 p-2 rounded-full">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold uppercase tracking-wider">{title}</h2>
          <p className="text-sm opacity-90">{description}</p>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full transition-colors">
          <X className="w-6 h-6" />
        </button>
      </div>
    </div>
  );
};
