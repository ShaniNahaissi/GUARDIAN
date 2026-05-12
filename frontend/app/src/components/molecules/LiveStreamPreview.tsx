import React, { useEffect, useRef, useState } from 'react';
import { getConsumerWebSocketUrl, getConsumerWebSocketUrlForBase } from '../../services/dataService';
import type { StreamTrackPayload } from '../../services/dataService';

interface LiveStreamPreviewProps {
  streamId: string;
  /** When set, open consumer WebSocket against this origin (must match producer backend). */
  consumerBackendOrigin?: string;
  className?: string;
}

/**
 * Subscribes to WS /consumer/{streamId}: binary JPEG then JSON tracks per frame.
 */
export const LiveStreamPreview: React.FC<LiveStreamPreviewProps> = ({
  streamId,
  consumerBackendOrigin,
  className = '',
}) => {
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle');
  const [lastMeta, setLastMeta] = useState<StreamTrackPayload | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const expectJsonRef = useRef(false);

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

  const trackHint =
    lastMeta && lastMeta.tracks.length > 0
      ? `${lastMeta.tracks.length} track(s) · seq ${lastMeta.frame_seq}`
      : lastMeta
        ? `seq ${lastMeta.frame_seq}`
        : '';

  return (
    <div className={`relative w-full h-full min-h-[120px] bg-gray-900 ${className}`}>
      {imgSrc ? (
        <img src={imgSrc} alt="" className="absolute inset-0 w-full h-full object-cover" />
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
