import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface AlertBannerProps {
  title: string;
  description: string;
  /** 'alert' (red, active) or 'idle' (neutral status). Always mounted at a fixed height so switching never shifts the layout. */
  variant?: 'alert' | 'idle';
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ title, description, variant = 'alert' }) => {
  const isAlert = variant === 'alert';
  return (
    <div
      className={`rounded-xl p-4 flex items-center gap-4 shadow-lg mb-6 transition-colors ${
        isAlert ? 'bg-guardian-danger text-white shadow-red-500/20' : 'bg-gray-900 border border-gray-800 text-guardian-muted'
      }`}
    >
      <div className={`p-2 rounded-full ${isAlert ? 'bg-white/20' : 'bg-gray-800'}`}>
        <AlertTriangle className="w-6 h-6" />
      </div>
      <div>
        <h2 className={`text-xl font-bold uppercase tracking-wider ${isAlert ? '' : 'text-white'}`}>{title}</h2>
        <p className="text-sm opacity-90">{description}</p>
      </div>
    </div>
  );
};
