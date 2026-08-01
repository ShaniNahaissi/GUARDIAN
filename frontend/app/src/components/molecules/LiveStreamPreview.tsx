import React, { useEffect, useRef, useState } from 'react';
import { getConsumerWebSocketUrl, getConsumerWebSocketUrlForBase } from '../../services/dataService';
import type { StreamTrackPayload } from '../../services/dataService';

interface LiveStreamPreviewProps {
  streamId: string;
  /** When set, open consumer WebSocket against this origin (must match producer backend). */
  consumerBackendOrigin?: string;
  className?: string;
  /** Fires whenever detection JSON arrives (or null after disconnect / teardown). */
  onTracksMeta?: (payload: StreamTrackPayload | null) => void;
}

/**
 * Subscribes to WS /consumer/{streamId}: binary JPEG then JSON tracks per frame.
 */
export const LiveStreamPreview: React.FC<LiveStreamPreviewProps> = ({
  streamId,
  consumerBackendOrigin,
  className = '',
  onTracksMeta,
}) => {
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle');
  const [lastMeta, setLastMeta] = useState<StreamTrackPayload | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const expectJsonRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [imgDim, setImgDim] = useState({ naturalWidth: 0, naturalHeight: 0 });
  const [clientDim, setClientDim] = useState({ width: 0, height: 0 });

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.target as HTMLImageElement;
    setImgDim({
      naturalWidth: target.naturalWidth,
      naturalHeight: target.naturalHeight
    });
  };

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setClientDim({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        });
      }
    });
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, []);

  /** Returns border + label color based on track class. */
  const getTrackColor = (className: string): string => {
    if (className === 'Gun' || className === 'Knife') return '#ef4444';        // red — weapon
    if (className.startsWith('Suspect (')) return '#dc2626';                    // bright red — active threat
    if (className === 'Suspect') return '#f59e0b';                             // amber — person tracked
    return '#60a5fa';                                                          // blue — fallback
  };

  const getBboxStyle = (bbox: [number, number, number, number]): React.CSSProperties => {
    const { naturalWidth, naturalHeight } = imgDim;
    const { width, height } = clientDim;
    if (!naturalWidth || !naturalHeight || !width || !height) return { display: 'none' };
    
    const scale = Math.max(width / naturalWidth, height / naturalHeight);
    const scaledWidth = naturalWidth * scale;
    const scaledHeight = naturalHeight * scale;
    const xOffset = (width - scaledWidth) / 2;
    const yOffset = (height - scaledHeight) / 2;
    
    const [x1, y1, x2, y2] = bbox;
    const left = xOffset + x1 * scale;
    const top = yOffset + y1 * scale;
    const boxWidth = (x2 - x1) * scale;
    const boxHeight = (y2 - y1) * scale;
    
    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${boxWidth}px`,
      height: `${boxHeight}px`,
      position: 'absolute',
      // Client-side interpolation: smooth bbox position/size transitions to further
      // reduce visual jitter on top of the backend's EMA-smoothed coordinates.
      transition: 'left 100ms linear, top 100ms linear, width 100ms linear, height 100ms linear',
    };
  };

  useEffect(() => {
    const id = streamId.trim();
    if (!id) {
      setStatus('idle');
      return;
    }

    const url = consumerBackendOrigin?.trim()
      ? getConsumerWebSocketUrlForBase(consumerBackendOrigin, id)
      : getConsumerWebSocketUrl(id);

    setStatus('connecting');
    expectJsonRef.current = false;
    const ws = new WebSocket(url);
    ws.binaryType = 'blob';
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('live');
    };

    ws.onmessage = (ev: MessageEvent<Blob | string>) => {
      if (typeof ev.data !== 'string') {
        if (blobUrlRef.current) {
          URL.revokeObjectURL(blobUrlRef.current);
        }
        blobUrlRef.current = URL.createObjectURL(ev.data);
        setImgSrc(blobUrlRef.current);
        expectJsonRef.current = true;
        return;
      }
      if (!expectJsonRef.current) {
        return;
      }
      expectJsonRef.current = false;
      try {
        const parsed = JSON.parse(ev.data) as StreamTrackPayload;
        setLastMeta(parsed);
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {
      setStatus('error');
    };

    ws.onclose = () => {
      setStatus((s) => (s === 'live' ? 'idle' : s));
    };

    return () => {
      ws.close();
      wsRef.current = null;
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setImgSrc(null);
      setLastMeta(null);
    };
  }, [streamId, consumerBackendOrigin]);

  useEffect(() => {
    onTracksMeta?.(lastMeta);
  }, [lastMeta, onTracksMeta]);

  const trackHint =
    lastMeta && lastMeta.tracks.length > 0
      ? `${lastMeta.tracks.length} track(s) · seq ${lastMeta.frame_seq}`
      : lastMeta
        ? `seq ${lastMeta.frame_seq}`
        : '';

  return (
    <div ref={containerRef} className={`relative w-full h-full min-h-[120px] bg-gray-900 overflow-hidden ${className}`}>
      {imgSrc ? (
        <>
          <img 
            src={imgSrc} 
            alt="" 
            className="absolute inset-0 w-full h-full object-cover" 
            onLoad={handleImageLoad}
          />
          {lastMeta?.tracks.map(track => {
            const color = getTrackColor(track.class_name);
            const isActiveThreat = track.class_name.startsWith('Suspect (');
            return (
              <div 
                key={track.track_id}
                className={`border-[3px] pointer-events-none z-20 flex flex-col items-start ${
                  isActiveThreat ? 'animate-pulse' : ''
                }`}
                style={{
                  ...getBboxStyle(track.bbox),
                  borderColor: color,
                  boxShadow: `0 0 10px ${color}80`,
                }}
              >
                <span
                  className="text-white text-xs font-bold px-1.5 py-0.5 rounded-sm whitespace-nowrap mt-[-24px]"
                  style={{ backgroundColor: color }}
                >
                  {track.class_name} {Math.round(track.confidence * 100)}%
                </span>
              </div>
            );
          })}
        </>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-guardian-muted text-xs px-3 text-center gap-1">
          {status === 'connecting' && <span>Connecting…</span>}
          {status === 'error' && <span>Stream error</span>}
          {(status === 'idle' || status === 'live') && !imgSrc && (
            <span>Waiting for frames (start producer with same stream id)</span>
          )}
        </div>
      )}
      {trackHint && (
        <div className="absolute bottom-2 left-2 right-2 text-[10px] sm:text-xs font-mono text-white/80 bg-black/50 rounded px-2 py-1 truncate">
          {trackHint}
        </div>
      )}
    </div>
  );
};
