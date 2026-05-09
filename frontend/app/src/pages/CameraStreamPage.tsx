import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Video, VideoOff, Wifi, WifiOff } from 'lucide-react';
import { Button } from '../components/atoms/Button';
import { Card } from '../components/atoms/Card';
import { useToast } from '../context/ToastContext';
import { getCameraStreamWebSocketUrl } from '../services/dataService';

interface CameraStreamPageProps {
  onBack: () => void;
}

const createDefaultStreamId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `stream-${Date.now()}`;
};

const getSupportedMimeType = (): string | null => {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
    'video/mp4',
  ];

  for (const mimeType of candidates) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }

  return null;
};

const getReadableMediaError = (error: unknown): string => {
  if (typeof window !== 'undefined' && !window.isSecureContext) {
    return 'Camera requires secure context. Open over HTTPS (or localhost).';
  }

  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError') {
      return 'Camera permission denied. Please allow camera access in browser settings.';
    }
    if (error.name === 'NotFoundError') {
      return 'No camera device found.';
    }
    if (error.name === 'NotReadableError') {
      return 'Camera is already in use by another app.';
    }
    if (error.name === 'OverconstrainedError') {
      return 'Requested camera constraints are not supported on this device.';
    }
  }

  return 'Could not start camera streaming';
};

export const CameraStreamPage: React.FC<CameraStreamPageProps> = ({ onBack }) => {
  const [streamUuid, setStreamUuid] = useState<string>(() => createDefaultStreamId());
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [sendToBackend, setSendToBackend] = useState(() => localStorage.getItem('guardian_use_backend') !== 'false');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState('Ready to start stream');
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileStreamIntervalRef = useRef<number | null>(null);
  const { showToast } = useToast();

  const stopStreaming = () => {
    if (fileStreamIntervalRef.current !== null) {
      window.clearInterval(fileStreamIntervalRef.current);
      fileStreamIntervalRef.current = null;
    }

    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsStreaming(false);
    setIsSocketConnected(false);
    setStatusMessage('Stream stopped');
  };

  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, []);

  const startStreaming = async () => {
    if (!streamUuid.trim()) {
      showToast('Please provide a stream UUID', 'error');
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      showToast('Camera API not available. Use HTTPS or localhost.', 'error');
      setStatusMessage('Camera API unavailable');
      return;
    }

    if (typeof MediaRecorder === 'undefined') {
      showToast('MediaRecorder is not supported in this browser', 'error');
      return;
    }

    const mimeType = getSupportedMimeType();
    if (!mimeType) {
      showToast('No supported recording format found', 'error');
      return;
    }

    try {
      setStatusMessage('Requesting camera permission...');
      let mediaStream: MediaStream;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
          audio: false,
        });
      } catch {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }
      mediaStreamRef.current = mediaStream;

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }

      if (sendToBackend) {
        const wsUrl = getCameraStreamWebSocketUrl(streamUuid);
        setStatusMessage(`Connecting to ${wsUrl}`);
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;
        socket.binaryType = 'arraybuffer';

        socket.onopen = () => {
          setIsSocketConnected(true);
          setStatusMessage('WebSocket connected. Streaming started.');
        };

        socket.onclose = () => {
          setIsSocketConnected(false);
          setStatusMessage('WebSocket disconnected');
        };

        socket.onerror = () => {
          setStatusMessage('WebSocket error (camera still running)');
        };
      } else {
        setStatusMessage('Offline demo mode: camera chunks are generated locally');
      }

      const recorder = new MediaRecorder(mediaStream, { mimeType, videoBitsPerSecond: 1_000_000 });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = async (event: BlobEvent) => {
        if (event.data.size === 0 || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }
        try {
          const payload = await event.data.arrayBuffer();
          wsRef.current.send(payload);
        } catch (error) {
          console.error('Failed to send media chunk', error);
        }
      };

      recorder.onerror = () => {
        setStatusMessage('Recorder error');
      };

      recorder.start(500);
      setIsStreaming(true);
      showToast('Camera stream started', 'success');
    } catch (error) {
      console.error('Failed to start stream', error);
      stopStreaming();
      const readableError = getReadableMediaError(error);
      setStatusMessage(readableError);
      showToast(readableError, 'error');
    }
  };

  const startFileStreaming = () => {
    if (!selectedFile) {
      showToast('Select a video file first', 'error');
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = objectUrl;
      void videoRef.current.play().catch(() => {
        // User gesture usually already exists from button click.
      });
    }

    if (sendToBackend) {
      const wsUrl = getCameraStreamWebSocketUrl(streamUuid);
      setStatusMessage(`Connecting to ${wsUrl}`);
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;
      socket.binaryType = 'arraybuffer';
      socket.onopen = () => {
        setIsSocketConnected(true);
        setStatusMessage('WebSocket connected. Streaming file chunks...');
      };
      socket.onclose = () => {
        setIsSocketConnected(false);
      };
      socket.onerror = () => {
        setStatusMessage('WebSocket error (offline file demo still running)');
      };
    } else {
      setStatusMessage('Offline demo mode: streaming file chunks locally');
    }

    const chunkSize = 64 * 1024;
    let offset = 0;
    setIsStreaming(true);
    showToast('File streaming started', 'success');

    fileStreamIntervalRef.current = window.setInterval(async () => {
      if (offset >= selectedFile.size) {
        stopStreaming();
        setStatusMessage('File stream completed');
        showToast('File stream completed', 'success');
        URL.revokeObjectURL(objectUrl);
        return;
      }

      const chunk = selectedFile.slice(offset, offset + chunkSize);
      offset += chunkSize;
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const data = await chunk.arrayBuffer();
        wsRef.current.send(data);
      }
    }, 200);
  };

  const wsUrlPreview = streamUuid.trim() ? getCameraStreamWebSocketUrl(streamUuid) : '';

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 sm:items-center sm:gap-4">
        <button onClick={onBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold mb-1">Camera Stream</h2>
          <p className="text-guardian-muted text-sm">Continuously stream camera video to backend WebSocket</p>
        </div>
      </div>

      <Card className="p-4 sm:p-6 space-y-5">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-guardian-muted">Stream UUID</label>
          <input
            type="text"
            value={streamUuid}
            onChange={(e) => setStreamUuid(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
            placeholder="camera-uuid"
            disabled={isStreaming}
          />
          <p className="text-xs text-guardian-muted break-all">Target socket: {wsUrlPreview || '-'}</p>
        </div>

        <label className="flex items-center gap-3 text-sm text-guardian-muted">
          <input
            type="checkbox"
            checked={sendToBackend}
            onChange={(e) => setSendToBackend(e.target.checked)}
            disabled={isStreaming}
          />
          Send chunks to backend WebSocket
        </label>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-guardian-muted">Fallback video file (works without camera API)</label>
          <input
            type="file"
            accept="video/*"
            capture="environment"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            disabled={isStreaming}
            className="block w-full text-sm text-guardian-muted file:mr-4 file:rounded-lg file:border-0 file:bg-gray-800 file:px-4 file:py-2 file:text-white hover:file:bg-gray-700"
          />
        </div>

        <div className="rounded-xl overflow-hidden border border-gray-800 bg-black min-h-[280px] flex items-center justify-center">
          <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2 text-sm">
            {isSocketConnected ? <Wifi className="w-4 h-4 text-guardian-success" /> : <WifiOff className="w-4 h-4 text-guardian-muted" />}
            <span className={isSocketConnected ? 'text-guardian-success' : 'text-guardian-muted'}>{statusMessage}</span>
          </div>
          <div className="flex w-full sm:w-auto gap-2">
            {!isStreaming ? (
              <Button className="flex-1 sm:flex-none" onClick={startStreaming}>
                <Video className="w-4 h-4" /> Start Streaming
              </Button>
            ) : (
              <Button className="flex-1 sm:flex-none" variant="danger" onClick={stopStreaming}>
                <VideoOff className="w-4 h-4" /> Stop Streaming
              </Button>
            )}
            {!isStreaming && (
              <Button className="flex-1 sm:flex-none" variant="secondary" onClick={startFileStreaming}>
                <Video className="w-4 h-4" /> Stream Selected File
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};
