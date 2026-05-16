import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Video, VideoOff, Wifi, WifiOff } from 'lucide-react';
import { Button } from '../components/atoms/Button';
import { Card } from '../components/atoms/Card';
import { useToast } from '../context/ToastContext';
import { useStreamingSession } from '../context/StreamingSessionContext';
import { buildAppUrlForHashView } from '../nav/appHash';
import { getProducerWebSocketUrl } from '../services/dataService';

interface CameraStreamPageProps {
  onBack: () => void;
}

const createDefaultStreamId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `stream-${Date.now()}`;
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

const JPEG_QUALITY = 0.85;
const JPEG_INTERVAL_MS = 120;

export const CameraStreamPage: React.FC<CameraStreamPageProps> = ({ onBack }) => {
  const [streamUuid, setStreamUuid] = useState<string>(() => createDefaultStreamId());
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [sendToBackend, setSendToBackend] = useState(() => localStorage.getItem('guardian_use_backend') !== 'false');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState('Ready to start stream');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const jpegIntervalRef = useRef<number | null>(null);
  const fileObjectUrlRef = useRef<string | null>(null);
  const { showToast } = useToast();
  const { setStreamingActive } = useStreamingSession();

  const clearJpegInterval = () => {
    if (jpegIntervalRef.current !== null) {
      window.clearInterval(jpegIntervalRef.current);
      jpegIntervalRef.current = null;
    }
  };

  const stopStreaming = () => {
    clearJpegInterval();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (fileObjectUrlRef.current) {
      URL.revokeObjectURL(fileObjectUrlRef.current);
      fileObjectUrlRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = '';
      videoRef.current.removeAttribute('src');
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

  useEffect(() => {
    setStreamingActive(isStreaming);
    return () => setStreamingActive(false);
  }, [isStreaming, setStreamingActive]);

  const handleBack = () => {
    if (isStreaming) {
      window.open(buildAppUrlForHashView('dashboard'), '_blank', 'noopener,noreferrer');
      return;
    }
    onBack();
  };

  const startJpegPump = () => {
    clearJpegInterval();
    jpegIntervalRef.current = window.setInterval(() => {
      const v = videoRef.current;
      const ws = wsRef.current;
      const canvas = canvasRef.current;
      if (!v || !canvas || !ws || ws.readyState !== WebSocket.OPEN) {
        return;
      }
      if (v.readyState < 2 || v.videoWidth === 0 || v.videoHeight === 0) {
        return;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return;
      }
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      ctx.drawImage(v, 0, 0);
      canvas.toBlob(
        (blob) => {
          if (blob && ws.readyState === WebSocket.OPEN) {
            ws.send(blob);
          }
        },
        'image/jpeg',
        JPEG_QUALITY,
      );
    }, JPEG_INTERVAL_MS);
  };

  const openProducerSocket = (onReady: () => void) => {
    const wsUrl = getProducerWebSocketUrl(streamUuid);
    setStatusMessage(`Connecting to ${wsUrl}`);
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
      setIsSocketConnected(true);
      setStatusMessage('WebSocket connected. Sending JPEG frames.');
      onReady();
    };

    socket.onclose = () => {
      setIsSocketConnected(false);
      clearJpegInterval();
      setStatusMessage('WebSocket disconnected');
    };

    socket.onerror = () => {
      setStatusMessage('WebSocket error');
    };
  };

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
        openProducerSocket(() => {
          startJpegPump();
        });
      } else {
        setStatusMessage('Local preview only (not sending to backend)');
      }

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
    fileObjectUrlRef.current = objectUrl;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = objectUrl;
      void videoRef.current.play().catch(() => {
        /* user gesture present from button */
      });
    }

    const v = videoRef.current;
    if (v) {
      const onEnded = () => {
        stopStreaming();
        setStatusMessage('File stream completed');
        showToast('File stream completed', 'success');
      };
      v.addEventListener('ended', onEnded, { once: true });
    }

    if (sendToBackend) {
      openProducerSocket(() => {
        startJpegPump();
      });
    } else {
      setStatusMessage('Playing file locally (not sending to backend)');
    }

    setIsStreaming(true);
    showToast('File streaming started', 'success');
  };

  const wsUrlPreview = streamUuid.trim() ? getProducerWebSocketUrl(streamUuid) : '';

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 sm:items-center sm:gap-4">
        <button type="button" onClick={handleBack} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <div>
          <h2 className="text-xl sm:text-2xl font-bold mb-1">Camera Stream</h2>
          <p className="text-guardian-muted text-sm">Send JPEG frames to the backend producer WebSocket</p>
        </div>
      </div>

      <Card className="p-4 sm:p-6 space-y-5">
        <canvas ref={canvasRef} className="hidden" aria-hidden="true" />
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
          <p className="text-xs text-guardian-muted break-all">Producer: {wsUrlPreview || '-'}</p>
        </div>

        <label className="flex items-center gap-3 text-sm text-guardian-muted">
          <input
            type="checkbox"
            checked={sendToBackend}
            onChange={(e) => setSendToBackend(e.target.checked)}
            disabled={isStreaming}
          />
          Send JPEG frames to backend WebSocket
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
              <Button className="flex-1 sm:flex-none" onClick={() => void startStreaming()}>
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
