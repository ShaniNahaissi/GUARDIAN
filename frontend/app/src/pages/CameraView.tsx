import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Button } from '../components/atoms/Button';
import { Badge } from '../components/atoms/Badge';
import { ThreatPanel } from '../components/molecules/ThreatPanel';
import { AlertBanner } from '../components/molecules/AlertBanner';
import { ArrowLeft, CircleDot, Camera, Maximize } from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { getCameras } from '../services/dataService';
import { LiveStreamPreview } from '../components/molecules/LiveStreamPreview';
import type { CameraInfo } from '../services/dataService';

interface CameraViewProps {
  cameraId: string;
  onBack: () => void;
}

/** HTTP(S) image or video URLs work in <img> / <video>. Empty imageUrl uses WS consumer live preview. */
const isVideoElementSource = (url: string): boolean => {
  const lower = url.trim().toLowerCase();
  if (!lower) return false;
  if (lower.includes('.m3u8')) return true;
  if (lower.endsWith('.mp4') || lower.endsWith('.webm') || lower.endsWith('.ogg')) return true;
  return false;
};

export const CameraView: React.FC<CameraViewProps> = ({ cameraId, onBack }) => {
  const [camera, setCamera] = useState<CameraInfo | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [showAlert, setShowAlert] = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const { showToast } = useToast();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await getCameras();
        if (cancelled) return;
        const found = list.find((c) => c.id === cameraId) ?? null;
        setCamera(found);
      } catch {
        if (!cancelled) setCamera(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  const streamUrl = camera?.imageUrl?.trim() ?? '';
  const useVideo = useMemo(() => isVideoElementSource(streamUrl), [streamUrl]);

  useEffect(() => {
    if (!useVideo || !streamUrl || !videoRef.current) return;
    void videoRef.current.play().catch(() => {
      showToast('Video stream could not autoplay. Use the player controls.', 'info');
    });
  }, [useVideo, streamUrl, showToast]);

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
      <div className="flex items-start gap-3 sm:items-center sm:gap-4 mb-6">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold">{camera?.name ?? 'Camera'}</h1>
          <p className="text-sm text-guardian-muted">
            {cameraId}
            {camera?.location ? ` • ${camera.location}` : ''}
          </p>
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
        <div ref={feedRef} className="lg:col-span-2 flex flex-col h-full min-h-[350px] bg-black rounded-xl border border-gray-800 overflow-hidden relative">
          <div className="absolute top-3 left-3 sm:top-4 sm:left-4 flex items-center gap-2 sm:gap-3 z-10">
            <div className={`w-3 h-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`}></div>
            <span className="font-bold drop-shadow-md text-sm sm:text-base">{camera?.name ?? cameraId}</span>
          </div>
          <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-10">
            <Badge status="critical">THREAT DETECTED</Badge>
          </div>
          <div className="absolute top-14 left-3 sm:top-16 sm:left-4 z-10">
            <Badge status="critical">WEAPON DETECTED</Badge>
          </div>

          <div className="flex-1 relative flex items-center justify-center bg-gray-900">
            {!streamUrl.trim() ? (
              <div className="absolute inset-0">
                <LiveStreamPreview streamId={cameraId} />
              </div>
            ) : useVideo ? (
              <video
                ref={videoRef}
                key={streamUrl}
                src={streamUrl}
                autoPlay
                playsInline
                muted
                controls
                className="absolute inset-0 w-full h-full object-cover opacity-90"
                onError={() => showToast('Video stream failed to load. Check URL and CORS.', 'error')}
              />
            ) : (
              <img
                src={streamUrl}
                alt="Camera feed"
                className="absolute inset-0 w-full h-full object-cover opacity-90"
                onError={() => showToast('Feed URL failed to load.', 'error')}
              />
            )}
            <div className="absolute border-2 border-red-500 w-36 h-48 sm:w-48 sm:h-64 top-1/3 left-1/3 shadow-[0_0_15px_rgba(239,68,68,0.5)] pointer-events-none" />
          </div>

          <div className="p-3 sm:p-4 bg-gray-900/80 backdrop-blur-sm border-t border-gray-800 flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center z-10">
            <div className="flex flex-wrap gap-2">
              <Button variant={isRecording ? 'danger' : 'secondary'} onClick={handleRecord}>
                <CircleDot className="w-4 h-4" /> {isRecording ? 'Stop Record' : 'Record'}
              </Button>
              <Button variant="secondary" onClick={handleSnapshot}>
                <Camera className="w-4 h-4" /> Snapshot
              </Button>
            </div>
            <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-4 text-guardian-muted">
              <span className="font-mono text-xs sm:text-sm">14:23:45 {isRecording && '| REC'}</span>
              <button className="hover:text-white" onClick={handleMaximize}>
                <Maximize className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <div className="h-full overflow-y-auto md:pr-2">
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
