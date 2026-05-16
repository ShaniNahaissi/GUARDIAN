import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Button } from '../components/atoms/Button';
import { Badge } from '../components/atoms/Badge';
import { ThreatPanel } from '../components/molecules/ThreatPanel';
import { AlertBanner } from '../components/molecules/AlertBanner';
import { ArrowLeft, CircleDot, Camera, Maximize } from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { getCameras } from '../services/dataService';
import { LiveStreamPreview } from '../components/molecules/LiveStreamPreview';
import type { CameraInfo, StreamTrackPayload } from '../services/dataService';

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

/** Model is weapon-only (e.g. Gun/Knife); any non-empty track list is an active detection. */
const hasWeaponTracks = (meta: StreamTrackPayload | null): boolean =>
  !!meta && Array.isArray(meta.tracks) && meta.tracks.length > 0;

function pickStrongestTrack(meta: StreamTrackPayload | null) {
  if (!meta?.tracks.length) return null;
  return meta.tracks.reduce((a, b) => (a.confidence >= b.confidence ? a : b));
}

function bboxCenterLabel(bbox: [number, number, number, number]): string {
  const [x1, y1, x2, y2] = bbox;
  const cx = Math.round((x1 + x2) / 2);
  const cy = Math.round((y1 + y2) / 2);
  return `${cx}, ${cy} px`;
}

export const CameraView: React.FC<CameraViewProps> = ({ cameraId, onBack }) => {
  const [camera, setCamera] = useState<CameraInfo | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [showAlert, setShowAlert] = useState(true);
  const [tracksMeta, setTracksMeta] = useState<StreamTrackPayload | null>(null);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [lastThreatTime, setLastThreatTime] = useState<string | null>(null);
  const prevWeaponRef = useRef(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const { showToast } = useToast();

  const handleTracksMeta = useCallback((payload: StreamTrackPayload | null) => {
    setTracksMeta(payload);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

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
  const useLiveConsumer = !streamUrl.trim();
  const useVideo = useMemo(() => isVideoElementSource(streamUrl), [streamUrl]);
  const weaponActive = useLiveConsumer && hasWeaponTracks(tracksMeta);

  useEffect(() => {
    if (weaponActive) {
      setLastThreatTime(new Date().toLocaleTimeString());
    }
  }, [weaponActive, tracksMeta?.frame_seq]);

  useEffect(() => {
    if (weaponActive && !prevWeaponRef.current) {
      setShowAlert(true);
    }
    if (!weaponActive && prevWeaponRef.current) {
      setShowAlert(true);
    }
    prevWeaponRef.current = weaponActive;
  }, [weaponActive]);

  useEffect(() => {
    if (!useVideo || !streamUrl || !videoRef.current) return;
    void videoRef.current.play().catch(() => {
      showToast('Video stream could not autoplay. Use the player controls.', 'info');
    });
  }, [useVideo, streamUrl, showToast]);

  const strongest = useMemo(() => pickStrongestTrack(tracksMeta), [tracksMeta]);
  const clockLabel = useMemo(() => new Date(nowTick).toLocaleTimeString(), [nowTick]);

  const threatPanelProps = useMemo(() => {
    if (!weaponActive || !strongest) {
      return {
        threatLevel: 'normal' as const,
        confidenceScore: 0,
        detectionAccuracy: '—',
        info: {
          objectType: '—',
          firstDetected: '—',
          locationInFrame: '—',
          distance: '—',
        },
      };
    }
    const pct = Math.round(strongest.confidence * 100);
    const accuracy = strongest.confidence >= 0.8 ? 'High' : strongest.confidence >= 0.5 ? 'Moderate' : 'Low';
    return {
      threatLevel: 'critical' as const,
      confidenceScore: pct,
      detectionAccuracy: accuracy,
      info: {
        objectType: strongest.class_name,
        firstDetected: lastThreatTime ?? new Date().toLocaleTimeString(),
        locationInFrame: bboxCenterLabel(strongest.bbox),
        distance: '—',
      },
    };
  }, [weaponActive, strongest, lastThreatTime]);

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

  const alertDescription =
    `${camera?.name ?? cameraId}${lastThreatTime ? ` | ${lastThreatTime}` : ''}`;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-start gap-3 sm:items-center sm:gap-4 mb-6">
        <button type="button" onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
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

      {weaponActive && showAlert && (
        <AlertBanner
          title="WEAPON DETECTED"
          description={alertDescription}
          onClose={() => {
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
          {weaponActive && (
            <>
              <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-10">
                <Badge status="critical">THREAT DETECTED</Badge>
              </div>
              <div className="absolute top-14 left-3 sm:top-16 sm:left-4 z-10">
                <Badge status="critical">WEAPON DETECTED</Badge>
              </div>
            </>
          )}

          <div className="flex-1 relative flex items-center justify-center bg-gray-900">
            {!streamUrl.trim() ? (
              <div className="absolute inset-0">
                <LiveStreamPreview streamId={cameraId} onTracksMeta={handleTracksMeta} />
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
              <span className="font-mono text-xs sm:text-sm">
                {clockLabel}
                {isRecording && ' | REC'}
              </span>
              <button type="button" className="hover:text-white" onClick={handleMaximize}>
                <Maximize className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <div className="h-full overflow-y-auto md:pr-2">
          <ThreatPanel
            threatLevel={threatPanelProps.threatLevel}
            confidenceScore={threatPanelProps.confidenceScore}
            detectionAccuracy={threatPanelProps.detectionAccuracy}
            info={threatPanelProps.info}
          />
        </div>
      </div>
    </div>
  );
};
