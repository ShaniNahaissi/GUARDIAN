import React from 'react';
import { Card } from '../atoms/Card';
import { Badge } from '../atoms/Badge';

interface ThreatInfo {
  objectType: string;
  firstDetected: string;
  locationInFrame: string;
  distance: string;
}

interface ThreatPanelProps {
  threatLevel: 'critical' | 'warning' | 'normal';
  confidenceScore: number;
  detectionAccuracy: string;
  info: ThreatInfo;
}

export const ThreatPanel: React.FC<ThreatPanelProps> = ({ threatLevel, confidenceScore, detectionAccuracy, info }) => {
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4 border-red-500/30">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold">Threat Level</h3>
          <Badge status={threatLevel}>{threatLevel.toUpperCase()}</Badge>
        </div>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-guardian-muted">Confidence Score</span>
              <span className="font-bold">{confidenceScore}%</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-red-500" style={{ width: `${confidenceScore}%` }}></div>
            </div>
          </div>
          
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-guardian-muted">Detection Accuracy</span>
              <span className="font-bold">{detectionAccuracy}</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-red-500" style={{ width: '85%' }}></div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="font-bold mb-4">Detection Information</h3>
        <ul className="space-y-3 text-sm">
          <li className="flex justify-between border-b border-gray-800 pb-2">
            <span className="text-guardian-muted">Object Type</span>
            <span className="font-medium">{info.objectType}</span>
          </li>
          <li className="flex justify-between border-b border-gray-800 pb-2">
            <span className="text-guardian-muted">First Detected</span>
            <span className="font-medium">{info.firstDetected}</span>
          </li>
          <li className="flex justify-between border-b border-gray-800 pb-2">
            <span className="text-guardian-muted">Location in Frame</span>
            <span className="font-medium">{info.locationInFrame}</span>
          </li>
          <li className="flex justify-between pb-1">
            <span className="text-guardian-muted">Distance</span>
            <span className="font-medium">{info.distance}</span>
          </li>
        </ul>
      </Card>
    </div>
  );
};
