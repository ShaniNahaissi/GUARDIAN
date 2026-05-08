import React from 'react';
import { Card } from '../atoms/Card';
import { Badge } from '../atoms/Badge';
import { Video, AlertTriangle, AlertCircle, ShieldAlert } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string;
  subValue: string;
  trend?: string;
  iconType: 'camera' | 'warning' | 'major' | 'critical';
  statusLabel: string;
  statusBadge: 'normal' | 'warning' | 'major' | 'critical';
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, subValue, trend, iconType, statusLabel, statusBadge }) => {
  const getIcon = () => {
    switch (iconType) {
      case 'camera': return <Video className="w-6 h-6 text-blue-400" />;
      case 'warning': return <AlertTriangle className="w-6 h-6 text-yellow-400" />;
      case 'major': return <AlertCircle className="w-6 h-6 text-orange-400" />;
      case 'critical': return <ShieldAlert className="w-6 h-6 text-red-400" />;
    }
  };

  const getBgColor = () => {
    switch (iconType) {
      case 'camera': return 'bg-blue-500/20';
      case 'warning': return 'bg-yellow-500/20';
      case 'major': return 'bg-orange-500/20';
      case 'critical': return 'bg-red-500/20';
    }
  };

  return (
    <Card className="p-5 flex flex-col justify-between">
      <div className="flex justify-between items-start mb-6">
        <div className={`p-3 rounded-lg ${getBgColor()}`}>
          {getIcon()}
        </div>
        <div className="text-right">
          <div className="text-sm text-guardian-muted">{trend || 'Last 24h'}</div>
          {trend && <div className="text-xs text-green-400">today</div>}
        </div>
      </div>
      
      <div className="mb-4">
        <div className="flex items-baseline gap-2 mb-1">
          <div className="text-4xl font-bold">{value}</div>
          <div className="text-sm text-guardian-muted font-semibold">{subValue}</div>
        </div>
        <div className="text-sm text-guardian-muted">{title}</div>
      </div>

      <div className="flex justify-between items-center text-xs mt-2 border-t border-gray-800 pt-3">
        <span className="text-guardian-muted">Status</span>
        <Badge status={statusBadge}>{statusLabel}</Badge>
      </div>
    </Card>
  );
};
