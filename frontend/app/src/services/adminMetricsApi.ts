import { getBackendUrl, isBackendEnabled } from './apiBase';
import { getStoredAccessToken } from './authApi';

export interface MetricsSummary {
  totalFramesProcessed: number;
  avgTotalLatencyMs: number;
  avgYoloLatencyMs: number;
  totalSequencesAnalyzed: number;
  threatsDetectedCount: number;
}

export interface FrameMetricPoint {
  timestamp: string | null;
  frameSeq: number;
  totalLatencyMs: number;
  yoloLatencyMs: number;
  trackCount: number;
  detectionsCount: number;
  cpuUtilization: number;
  gpuVramUsed: number;
}

export interface SequenceMetricItem {
  timestamp: string | null;
  streamId: string;
  trackId: number;
  startFrameSeq: number;
  endFrameSeq: number;
  actionLabel: string;
  actionConfidence: number;
  bestFrameSeq: number;
  bestFrameScore: number;
  avgTotalLatencyMs: number;
  avgYoloLatencyMs: number;
  frameCount: number;
}

interface BackendMetricsSummary {
  total_frames_processed: number;
  avg_total_latency_ms: number;
  avg_yolo_latency_ms: number;
  total_sequences_analyzed: number;
  threats_detected_count: number;
}

interface BackendFrameMetricPoint {
  timestamp: string | null;
  frame_seq: number;
  total_latency_ms: number;
  yolo_latency_ms: number;
  track_count: number;
  detections_count: number;
  cpu_utilization: number;
  gpu_vram_used: number;
}

interface BackendSequenceMetricItem {
  timestamp: string | null;
  stream_id: string;
  track_id: number;
  start_frame_seq: number;
  end_frame_seq: number;
  action_label: string;
  action_confidence: number;
  best_frame_seq: number;
  best_frame_score: number;
  avg_total_latency_ms: number;
  avg_yolo_latency_ms: number;
  frame_count: number;
}

const headersJson = (): HeadersInit => {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  const t = getStoredAccessToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
};

// Mock summary data generator
const getMockSummary = (): MetricsSummary => ({
  totalFramesProcessed: 14205,
  avgTotalLatencyMs: 38.45,
  avgYoloLatencyMs: 22.12,
  totalSequencesAnalyzed: 412,
  threatsDetectedCount: 18,
});

// Mock frame series data generator
const getMockFrameSeries = (limit: number = 30): FrameMetricPoint[] => {
  const points: FrameMetricPoint[] = [];
  const now = new Date();
  for (let i = limit - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 1000);
    const baseTotal = 35 + Math.sin(i / 3) * 5 + Math.random() * 8;
    const baseYolo = 20 + Math.sin(i / 3) * 2 + Math.random() * 4;
    points.push({
      timestamp: time.toISOString(),
      frameSeq: 1000 + (limit - i),
      totalLatencyMs: Math.round(baseTotal * 100) / 100,
      yoloLatencyMs: Math.round(baseYolo * 100) / 100,
      trackCount: Math.random() > 0.5 ? 2 : 1,
      detectionsCount: Math.random() > 0.7 ? 2 : 1,
      cpuUtilization: Math.round((25 + Math.random() * 10) * 10) / 10,
      gpuVramUsed: 480 + Math.round(Math.random() * 30),
    });
  }
  return points;
};

// Mock sequences data generator
const getMockSequences = (): SequenceMetricItem[] => [
  {
    timestamp: new Date(Date.now() - 30000).toISOString(),
    streamId: 'CAM-001',
    trackId: 4,
    startFrameSeq: 120,
    endFrameSeq: 150,
    actionLabel: 'Shooting',
    actionConfidence: 0.9452,
    bestFrameSeq: 135,
    bestFrameScore: 0.9124,
    avgTotalLatencyMs: 37.82,
    avgYoloLatencyMs: 21.45,
    frameCount: 30,
  },
  {
    timestamp: new Date(Date.now() - 120000).toISOString(),
    streamId: 'CAM-001',
    trackId: 2,
    startFrameSeq: 50,
    endFrameSeq: 80,
    actionLabel: 'Violence',
    actionConfidence: 0.8123,
    bestFrameSeq: 68,
    bestFrameScore: 0.8415,
    avgTotalLatencyMs: 39.12,
    avgYoloLatencyMs: 22.04,
    frameCount: 30,
  },
  {
    timestamp: new Date(Date.now() - 250000).toISOString(),
    streamId: 'CAM-007',
    trackId: 1,
    startFrameSeq: 140,
    endFrameSeq: 170,
    actionLabel: 'Stabbing',
    actionConfidence: 0.8847,
    bestFrameSeq: 155,
    bestFrameScore: 0.8931,
    avgTotalLatencyMs: 36.54,
    avgYoloLatencyMs: 20.81,
    frameCount: 30,
  },
];

export async function fetchMetricsSummary(): Promise<MetricsSummary> {
  if (!isBackendEnabled()) return Promise.resolve(getMockSummary());
  try {
    const res = await fetch(`${getBackendUrl()}/admin/metrics/summary`, { headers: headersJson() });
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = (await res.json()) as BackendMetricsSummary;
    return {
      totalFramesProcessed: data.total_frames_processed,
      avgTotalLatencyMs: data.avg_total_latency_ms,
      avgYoloLatencyMs: data.avg_yolo_latency_ms,
      totalSequencesAnalyzed: data.total_sequences_analyzed,
      threatsDetectedCount: data.threats_detected_count,
    };
  } catch (e) {
    console.error('Failed to fetch metrics summary from backend, fallback to mock', e);
    return getMockSummary();
  }
}

export async function fetchFrameSeries(limit: number = 50): Promise<FrameMetricPoint[]> {
  if (!isBackendEnabled()) return Promise.resolve(getMockFrameSeries(limit));
  try {
    const res = await fetch(`${getBackendUrl()}/admin/metrics/frame-series?limit=${limit}`, { headers: headersJson() });
    if (!res.ok) throw new Error('Failed to fetch frame series');
    const data = (await res.json()) as BackendFrameMetricPoint[];
    return data.map((item) => ({
      timestamp: item.timestamp,
      frameSeq: item.frame_seq,
      totalLatencyMs: item.total_latency_ms,
      yoloLatencyMs: item.yolo_latency_ms,
      trackCount: item.track_count,
      detectionsCount: item.detections_count,
      cpuUtilization: item.cpu_utilization,
      gpuVramUsed: item.gpu_vram_used,
    }));
  } catch (e) {
    console.error('Failed to fetch frame series from backend, fallback to mock', e);
    return getMockFrameSeries(limit);
  }
}

export async function fetchSequences(limit: number = 30): Promise<SequenceMetricItem[]> {
  if (!isBackendEnabled()) return Promise.resolve(getMockSequences());
  try {
    const res = await fetch(`${getBackendUrl()}/admin/metrics/sequences?limit=${limit}`, { headers: headersJson() });
    if (!res.ok) throw new Error('Failed to fetch sequences');
    const data = (await res.json()) as BackendSequenceMetricItem[];
    return data.map((item) => ({
      timestamp: item.timestamp,
      streamId: item.stream_id,
      trackId: item.track_id,
      startFrameSeq: item.start_frame_seq,
      endFrameSeq: item.end_frame_seq,
      actionLabel: item.action_label,
      actionConfidence: item.action_confidence,
      bestFrameSeq: item.best_frame_seq,
      bestFrameScore: item.best_frame_score,
      avgTotalLatencyMs: item.avg_total_latency_ms,
      avgYoloLatencyMs: item.avg_yolo_latency_ms,
      frameCount: item.frame_count,
    }));
  } catch (e) {
    console.error('Failed to fetch sequences from backend, fallback to mock', e);
    return getMockSequences();
  }
}
