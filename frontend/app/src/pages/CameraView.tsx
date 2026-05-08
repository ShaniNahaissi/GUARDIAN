import React, { useState, useRef } from 'react';
import { Button } from '../components/atoms/Button';
import { Badge } from '../components/atoms/Badge';
import { ThreatPanel } from '../components/molecules/ThreatPanel';
import { AlertBanner } from '../components/molecules/AlertBanner';
import { ArrowLeft, CircleDot, Camera, Maximize } from 'lucide-react';
import { useToast } from '../context/ToastContext';

interface CameraViewProps {
  cameraId: string;
  onBack: () => void;
}

export const CameraView: React.FC<CameraViewProps> = ({ cameraId, onBack }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [showAlert, setShowAlert] = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);
  const { showToast } = useToast();

  const handleRecord = () => {
    if (isRecording) {
      setIsRecording(false);
      console.log(`Stopped recording ${cameraId}. Sending to backend...`);
      showToast('Recording stopped. Video sent to backend.', 'success');
    } else {
      setIsRecording(true);
    }
  };

  const handleSnapshot = () => {
    console.log(`Snapshot taken for ${cameraId}. Sending to backend...`);
    showToast('Snapshot captured. Image sent to backend.', 'success');
  };

  const handleMaximize = () => {
    if (feedRef.current) {
      if (!document.fullscreenElement) {
        feedRef.current.requestFullscreen().catch((err) => {
          showToast(`Error attempting to enable fullscreen: ${err.message}`, 'error');
        });
      } else {
        document.exitFullscreen();
      }
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">Main Entrance - Parking</h1>
          <p className="text-sm text-guardian-muted">{cameraId} • Building A - North Wing</p>
        </div>
      </div>

      {showAlert && (
        <AlertBanner 
          title="WEAPON DETECTED" 
          description="Camera 03 - Main Entrance | 14:23:45" 
          onClose={() => {
            console.log('Sending close alert to backend...');
            setShowAlert(false);
          }} 
        />
      )}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        <div ref={feedRef} className="lg:col-span-2 flex flex-col h-full bg-black rounded-xl border border-gray-800 overflow-hidden relative">
          <div className="absolute top-4 left-4 flex items-center gap-3 z-10">
            <div className={`w-3 h-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`}></div>
            <span className="font-bold drop-shadow-md">Camera 03 - Main Entrance</span>
          </div>
          <div className="absolute top-4 right-4 z-10">
            <Badge status="critical">THREAT DETECTED</Badge>
          </div>
          <div className="absolute top-16 left-4 z-10">
            <Badge status="critical">WEAPON DETECTED</Badge>
          </div>

          <div className="flex-1 relative flex items-center justify-center bg-gray-900">
            <img 
              src="https://images.unsplash.com/photo-1542204165-65bf26472b9b?auto=format&fit=crop&q=80&w=1200" 
              alt="Camera Feed" 
              className="absolute inset-0 w-full h-full object-cover opacity-60"
            />
            <div className="absolute border-2 border-red-500 w-48 h-64 top-1/3 left-1/3 shadow-[0_0_15px_rgba(239,68,68,0.5)]"></div>
          </div>

          <div className="p-4 bg-gray-900/80 backdrop-blur-sm border-t border-gray-800 flex justify-between items-center z-10">
            <div className="flex gap-2">
              <Button variant={isRecording ? 'danger' : 'secondary'} onClick={handleRecord}>
                <CircleDot className="w-4 h-4" /> {isRecording ? 'Stop Record' : 'Record'}
              </Button>
              <Button variant="secondary" onClick={handleSnapshot}>
                <Camera className="w-4 h-4" /> Snapshot
              </Button>
            </div>
            <div className="flex items-center gap-4 text-guardian-muted">
              <span className="font-mono text-sm">14:23:45 {isRecording && '| REC'}</span>
              <button className="hover:text-white" onClick={handleMaximize}>
                <Maximize className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <div className="h-full overflow-y-auto pr-2">
          <ThreatPanel 
            threatLevel="critical" 
            confidenceScore={98.7} 
            detectionAccuracy="High" 
            info={{
              objectType: 'Handgun',
              firstDetected: '23:47:15',
              locationInFrame: 'Center-Right',
              distance: '~15 meters'
            }}
          />
        </div>
      </div>
    </div>
  );
};
