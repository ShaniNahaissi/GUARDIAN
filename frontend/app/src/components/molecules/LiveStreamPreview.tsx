import React, { useEffect, useRef, useState } from 'react';
import { getConsumerWebSocketUrl, getConsumerWebSocketUrlForBase } from '../../services/dataService';
import type { StreamTrackPayload } from '../../services/dataService';

interface LiveStreamPreviewProps {
  streamId: string;
  consumerBackendOrigin?: string;
  className?: string;
  onTracksMeta?: (payload: StreamTrackPayload | null) => void;
}

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
  
  // 2. Animation Frame Synchronization (Canvas replacing DOM overlays)
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgDimRef = useRef({ naturalWidth: 0, naturalHeight: 0 });
  const clientDimRef = useRef({ width: 0, height: 0 });
  const lastMetaRef = useRef<StreamTrackPayload | null>(null);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.target as HTMLImageElement;
    imgDimRef.current = {
      naturalWidth: target.naturalWidth,
      naturalHeight: target.naturalHeight
    };
  };

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        clientDimRef.current = {
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        };
      }
    });
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, []);

  const getTrackColor = (className: string): string => {
    if (className === 'Gun' || className === 'Knife') return '#ef4444';
    if (className.startsWith('Suspect (')) return '#dc2626';
    if (className === 'Suspect') return '#f59e0b';
    return '#60a5fa';
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
      setLastMeta(null);
      lastMetaRef.current = null;
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
        
        // 1. Explicit Empty-Frame Reset & 3. Immutability & Object Equality
        if (!parsed.tracks || parsed.tracks.length === 0) {
          const emptyMeta = { ...parsed, tracks: [] };
          setLastMeta(emptyMeta);
          lastMetaRef.current = emptyMeta;
        } else {
          const freshMeta = { ...parsed, tracks: [...parsed.tracks] };
          setLastMeta(freshMeta);
          lastMetaRef.current = freshMeta;
        }
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {
      setStatus('error');
      setLastMeta(null);
      lastMetaRef.current = null;
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
      lastMetaRef.current = null;
    };
  }, [streamId, consumerBackendOrigin]);

  useEffect(() => {
    onTracksMeta?.(lastMeta);
  }, [lastMeta, onTracksMeta]);

  // Animation Loop for perfectly synchronized Canvas rendering
  useEffect(() => {
    let animationFrameId: number;

    const renderLoop = () => {
      animationFrameId = requestAnimationFrame(renderLoop);
      
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (!canvas || !ctx) return;
      
      const { width, height } = clientDimRef.current;
      const { naturalWidth, naturalHeight } = imgDimRef.current;
      
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      
      // On EVERY frame tick: execute a full canvas clear
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const meta = lastMetaRef.current;
      
      // Explicit Empty-Frame Reset: break out immediately if no tracks exist
      if (!meta || !meta.tracks || meta.tracks.length === 0) {
        return;
      }
      
      if (!naturalWidth || !naturalHeight || !width || !height) return;
      
      const scale = Math.max(width / naturalWidth, height / naturalHeight);
      const scaledWidth = naturalWidth * scale;
      const scaledHeight = naturalHeight * scale;
      const xOffset = (width - scaledWidth) / 2;
      const yOffset = (height - scaledHeight) / 2;
      
      meta.tracks.forEach(track => {
        const [x1, y1, x2, y2] = track.bbox;
        const rawLeft = xOffset + x1 * scale;
        const rawTop = yOffset + y1 * scale;
        const rawRight = xOffset + x2 * scale;
        const rawBottom = yOffset + y2 * scale;
        
        const clampedLeft = Math.max(0, rawLeft);
        const clampedTop = Math.max(0, rawTop);
        const clampedRight = Math.min(width, rawRight);
        const clampedBottom = Math.min(height, rawBottom);
        const clampedWidth = clampedRight - clampedLeft;
        const clampedHeight = clampedBottom - clampedTop;
        
        if (clampedWidth <= 0 || clampedHeight <= 0) return;
        
        const color = getTrackColor(track.class_name);
        const isActiveThreat = track.class_name.startsWith('Suspect (');
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        
        if (isActiveThreat) {
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
        }
        
        ctx.strokeRect(clampedLeft, clampedTop, clampedWidth, clampedHeight);
        ctx.shadowBlur = 0;
        
        const text = `${track.class_name} ${Math.round(track.confidence * 100)}%`;
        ctx.font = "bold 12px sans-serif";
        const textMetrics = ctx.measureText(text);
        const textWidth = textMetrics.width;
        
        ctx.fillStyle = color;
        ctx.fillRect(clampedLeft, clampedTop - 20, textWidth + 8, 20);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(text, clampedLeft + 4, clampedTop - 5);
      });
    };
    
    renderLoop();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

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
          <canvas
            ref={canvasRef}
            className="absolute inset-0 z-20 pointer-events-none"
          />
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
        <div className="absolute bottom-2 left-2 right-2 text-[10px] sm:text-xs font-mono text-white/80 bg-black/50 rounded px-2 py-1 truncate z-30">
          {trackHint}
        </div>
      )}
    </div>
  );
};
