import React, { useEffect, useState, useCallback } from 'react';
import { 
  Activity, 
  Cpu, 
  Database, 
  Timer, 
  RefreshCw, 
  ShieldAlert,
  Server,
  Flame,
  AlertTriangle
} from 'lucide-react';
import { Card } from '../atoms/Card';
import { Button } from '../atoms/Button';
import { 
  fetchMetricsSummary, 
  fetchFrameSeries, 
  fetchSequences 
} from '../../services/adminMetricsApi';
import type { 
  MetricsSummary, 
  FrameMetricPoint, 
  SequenceMetricItem 
} from '../../services/adminMetricsApi';

export const AdminMetricsDashboard: React.FC = () => {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [frameSeries, setFrameSeries] = useState<FrameMetricPoint[]>([]);
  const [sequences, setSequences] = useState<SequenceMetricItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const refreshInterval = 3000; // 3 seconds
  const [hoveredPoint, setHoveredPoint] = useState<FrameMetricPoint | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [sumData, seriesData, seqData] = await Promise.all([
        fetchMetricsSummary(),
        fetchFrameSeries(35),
        fetchSequences(15),
      ]);
      setSummary(sumData);
      setFrameSeries(seriesData);
      setSequences(seqData);
    } catch (e) {
      console.error('Failed to reload dashboard metrics', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(() => {
      void loadData();
    }, refreshInterval);
    return () => clearInterval(t);
  }, [autoRefresh, refreshInterval, loadData]);

  // Compute stats for threat distribution
  const threatCounts = {
    Normal: 0,
    Shooting: 0,
    Stabbing: 0,
    Violence: 0,
  };
  sequences.forEach((s) => {
    const label = s.actionLabel as keyof typeof threatCounts;
    if (label in threatCounts) {
      threatCounts[label]++;
    } else {
      threatCounts.Normal++;
    }
  });

  // Render SVG Line Chart for Latency
  const renderLatencyChart = () => {
    if (frameSeries.length < 2) {
      return (
        <div className="h-60 flex items-center justify-center text-guardian-muted">
          No latency data available
        </div>
      );
    }

    const width = 500;
    const height = 180;
    const paddingLeft = 40;
    const paddingRight = 10;
    const paddingTop = 15;
    const paddingBottom = 20;

    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;

    // Find max value to scale Y-axis (min 40ms for better scale)
    const maxVal = Math.max(
      40,
      ...frameSeries.map((d) => Math.max(d.totalLatencyMs, d.yoloLatencyMs))
    ) * 1.1;

    const pointsTotal: string[] = [];
    const pointsYolo: string[] = [];

    frameSeries.forEach((d, i) => {
      const x = paddingLeft + (i / (frameSeries.length - 1)) * chartWidth;
      
      const yTotal = height - paddingBottom - (d.totalLatencyMs / maxVal) * chartHeight;
      const yYolo = height - paddingBottom - (d.yoloLatencyMs / maxVal) * chartHeight;

      pointsTotal.push(`${x},${yTotal}`);
      pointsYolo.push(`${x},${yYolo}`);
    });

    const dTotal = `M ${pointsTotal.join(' L ')}`;
    const dYolo = `M ${pointsYolo.join(' L ')}`;

    return (
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible select-none">
          {/* Grids and Axes */}
          <line
            x1={paddingLeft}
            y1={paddingTop}
            x2={paddingLeft}
            y2={height - paddingBottom}
            className="stroke-gray-800"
            strokeWidth={1}
          />
          <line
            x1={paddingLeft}
            y1={height - paddingBottom}
            x2={width - paddingRight}
            y2={height - paddingBottom}
            className="stroke-gray-800"
            strokeWidth={1}
          />

          {/* Grid lines (horizontal) */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = paddingTop + ratio * chartHeight;
            const val = Math.round(maxVal * (1 - ratio));
            return (
              <g key={ratio} className="opacity-40">
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={width - paddingRight}
                  y2={y}
                  className="stroke-gray-800 stroke-dasharray-[2,2]"
                  strokeWidth={1}
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 4}
                  className="text-[9px] fill-guardian-muted text-right font-mono"
                  textAnchor="end"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Chronological Label */}
          <text
            x={paddingLeft}
            y={height - 5}
            className="text-[8px] fill-guardian-muted font-mono"
          >
            Older frames
          </text>
          <text
            x={width - paddingRight}
            y={height - 5}
            className="text-[8px] fill-guardian-muted font-mono"
            textAnchor="end"
          >
            Live
          </text>

          {/* YOLO Latency Area (underlying) */}
          <path
            d={`${dYolo} L ${paddingLeft + chartWidth},${height - paddingBottom} L ${paddingLeft},${height - paddingBottom} Z`}
            className="fill-blue-500/5 stroke-none"
          />
          {/* Total Latency Area (underlying) */}
          <path
            d={`${dTotal} L ${paddingLeft + chartWidth},${height - paddingBottom} L ${paddingLeft},${height - paddingBottom} Z`}
            className="fill-guardian-accent/5 stroke-none"
          />

          {/* Lines */}
          <path
            d={dYolo}
            fill="none"
            className="stroke-blue-500"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={dTotal}
            fill="none"
            className="stroke-guardian-accent"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Mouse Hover Overlay circles */}
          {frameSeries.map((d, i) => {
            const x = paddingLeft + (i / (frameSeries.length - 1)) * chartWidth;
            const yTotal = height - paddingBottom - (d.totalLatencyMs / maxVal) * chartHeight;

            return (
              <g
                key={i}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredPoint(d)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <circle
                  cx={x}
                  cy={yTotal}
                  r={hoveredPoint?.frameSeq === d.frameSeq ? 5 : 3}
                  className={`transition-all ${hoveredPoint?.frameSeq === d.frameSeq ? 'fill-guardian-accent stroke-white' : 'fill-guardian-accent/0 stroke-none'}`}
                  strokeWidth={1.5}
                />
                {/* Transparent wider hit zone */}
                <rect
                  x={x - chartWidth / (frameSeries.length * 2)}
                  y={paddingTop}
                  width={chartWidth / frameSeries.length}
                  height={chartHeight}
                  className="fill-transparent stroke-none"
                />
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {hoveredPoint && (
          <div className="absolute top-2 right-2 bg-gray-900/90 border border-gray-700 rounded-lg p-2 text-[10px] font-mono shadow-md backdrop-blur-sm z-10 space-y-1">
            <div className="text-white font-bold border-b border-gray-800 pb-1">
              Seq #{hoveredPoint.frameSeq}
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-guardian-muted">Total Pipeline:</span>
              <span className="text-guardian-accent font-bold">{hoveredPoint.totalLatencyMs} ms</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-guardian-muted">YOLO Inference:</span>
              <span className="text-blue-400 font-bold">{hoveredPoint.yoloLatencyMs} ms</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-guardian-muted">Track / Dets:</span>
              <span className="text-white font-bold">{hoveredPoint.trackCount} / {hoveredPoint.detectionsCount}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-guardian-muted">CPU Use:</span>
              <span className="text-white font-bold">{hoveredPoint.cpuUtilization}%</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-guardian-muted">GPU VRAM:</span>
              <span className="text-white font-bold">{hoveredPoint.gpuVramUsed} MB</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render SVG Bar Chart for Threat counts
  const renderThreatChart = () => {
    const data = [
      { name: 'Normal', count: threatCounts.Normal, color: 'fill-gray-600' },
      { name: 'Violence', count: threatCounts.Violence, color: 'fill-yellow-500' },
      { name: 'Stabbing', count: threatCounts.Stabbing, color: 'fill-orange-500' },
      { name: 'Shooting', count: threatCounts.Shooting, color: 'fill-red-500' },
    ];

    const maxCount = Math.max(1, ...data.map((d) => d.count));
    const width = 300;
    const height = 150;
    const barWidth = 45;
    const spacing = 20;
    const paddingBottom = 20;
    const paddingTop = 20;

    const chartHeight = height - paddingBottom - paddingTop;

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible select-none">
        {data.map((d, i) => {
          const barHeight = (d.count / maxCount) * chartHeight;
          const x = spacing + i * (barWidth + spacing);
          const y = height - paddingBottom - barHeight;

          return (
            <g key={d.name}>
              {/* Count value */}
              <text
                x={x + barWidth / 2}
                y={y - 6}
                textAnchor="middle"
                className="text-[10px] fill-white font-bold font-mono"
              >
                {d.count}
              </text>
              {/* Rounded top rect */}
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={4}
                className={`${d.color} opacity-85 hover:opacity-100 transition-opacity`}
              />
              {/* Label */}
              <text
                x={x + barWidth / 2}
                y={height - 5}
                textAnchor="middle"
                className="text-[9px] fill-guardian-muted font-semibold"
              >
                {d.name}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  const getLatencyColor = (ms: number) => {
    if (ms < 35) return 'text-guardian-success';
    if (ms < 70) return 'text-guardian-warning';
    return 'text-guardian-danger';
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  const getThreatBadge = (label: string) => {
    switch (label) {
      case 'Shooting':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-red-950/60 border border-red-500/50 text-red-400 rounded-full flex items-center gap-1 w-fit">
            <Flame className="w-3.5 h-3.5" /> Shooting
          </span>
        );
      case 'Stabbing':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-orange-950/60 border border-orange-500/50 text-orange-400 rounded-full flex items-center gap-1 w-fit">
            <AlertTriangle className="w-3.5 h-3.5" /> Stabbing
          </span>
        );
      case 'Violence':
        return (
          <span className="px-2 py-0.5 text-xs font-bold bg-yellow-950/60 border border-yellow-500/50 text-yellow-400 rounded-full flex items-center gap-1 w-fit">
            <ShieldAlert className="w-3.5 h-3.5" /> Violence
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-xs font-medium bg-gray-800/80 border border-gray-700/60 text-guardian-muted rounded-full w-fit">
            Normal
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
            <Activity className="w-7 h-7 text-guardian-accent shrink-0 animate-pulse" />
            Model Metrics & Diagnostics
          </h2>
          <p className="text-guardian-muted text-sm mt-1">
            Real-time inference profiling, performance aggregation, and behavioral sequence tracking logs.
          </p>
        </div>
        
        <div className="flex items-center gap-3 shrink-0">
          <label className="flex items-center gap-2 text-xs font-medium text-guardian-muted bg-gray-900 border border-gray-800 px-3 py-2 rounded-lg cursor-pointer hover:border-gray-700 transition-colors">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-guardian-accent"
            />
            Auto-refresh
          </label>
          <Button 
            variant="secondary" 
            onClick={() => void loadData()}
            disabled={loading}
            className="h-9 px-3 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 sm:p-5 flex items-center gap-4 bg-gray-900/40">
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl shrink-0">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-guardian-muted uppercase tracking-wider font-semibold">Total Frames</div>
            <div className="text-xl sm:text-2xl font-bold mt-1 font-mono">
              {summary ? summary.totalFramesProcessed.toLocaleString() : '—'}
            </div>
          </div>
        </Card>

        <Card className="p-4 sm:p-5 flex items-center gap-4 bg-gray-900/40">
          <div className="p-3 bg-guardian-accent/10 text-guardian-accent rounded-xl shrink-0">
            <Timer className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-guardian-muted uppercase tracking-wider font-semibold">Avg Pipeline</div>
            <div className="text-xl sm:text-2xl font-bold mt-1 font-mono flex items-baseline gap-1">
              <span className={summary ? getLatencyColor(summary.avgTotalLatencyMs) : ''}>
                {summary ? summary.avgTotalLatencyMs.toFixed(1) : '—'}
              </span>
              <span className="text-[10px] text-guardian-muted font-normal">ms</span>
            </div>
          </div>
        </Card>

        <Card className="p-4 sm:p-5 flex items-center gap-4 bg-gray-900/40">
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl shrink-0">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-guardian-muted uppercase tracking-wider font-semibold">Avg YOLOv8</div>
            <div className="text-xl sm:text-2xl font-bold mt-1 font-mono flex items-baseline gap-1">
              <span className="text-purple-400">
                {summary ? summary.avgYoloLatencyMs.toFixed(1) : '—'}
              </span>
              <span className="text-[10px] text-guardian-muted font-normal">ms</span>
            </div>
          </div>
        </Card>

        <Card className="p-4 sm:p-5 flex items-center gap-4 bg-gray-900/40">
          <div className="p-3 bg-red-500/10 text-red-400 rounded-xl shrink-0">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-guardian-muted uppercase tracking-wider font-semibold">Threat Sequences</div>
            <div className="text-xl sm:text-2xl font-bold mt-1 font-mono text-red-400">
              {summary ? summary.threatsDetectedCount : '—'}
            </div>
          </div>
        </Card>
      </div>

      {/* Visual Analytics graphs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-guardian-accent" />
              Inference Latency Timeline (ms)
            </h3>
            <div className="flex items-center gap-4 text-[10px] font-mono">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-guardian-accent inline-block" />
                <span className="text-guardian-muted">Total Pipeline</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
                <span className="text-guardian-muted">YOLOv8 Run</span>
              </div>
            </div>
          </div>
          {renderLatencyChart()}
        </Card>

        <Card className="p-5">
          <h3 className="font-bold text-sm text-white border-b border-gray-800 pb-3 mb-4 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            Threat Sequence Types
          </h3>
          <div className="flex flex-col h-60 justify-between">
            <div className="flex-1 flex items-center justify-center">
              {renderThreatChart()}
            </div>
            <div className="text-[10px] text-guardian-muted text-center pt-2 font-mono border-t border-gray-800/40">
              Analysis based on recent {sequences.length} temporal window runs
            </div>
          </div>
        </Card>
      </div>

      {/* Recent threat sequences log list */}
      <Card className="border border-gray-800 overflow-hidden">
        <div className="p-4 sm:p-5 bg-gray-900/30 border-b border-gray-800 flex items-center justify-between">
          <h3 className="font-bold text-sm text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-guardian-accent" />
            Behavioral Sequence Classification Log
          </h3>
          <span className="px-2 py-0.5 text-[10px] bg-gray-800 text-guardian-muted rounded font-mono font-bold">
            Recent {sequences.length} Entries
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/10 text-xs font-semibold text-guardian-muted tracking-wider">
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Stream</th>
                <th className="px-4 py-3 font-mono">Track ID</th>
                <th className="px-4 py-3">Classification</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Top-Performing Frame (Peak Threat)</th>
                <th className="px-4 py-3 font-mono">Avg Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-xs">
              {sequences.map((s, idx) => (
                <tr key={idx} className="hover:bg-gray-900/30 transition-colors">
                  <td className="px-4 py-3 text-guardian-muted whitespace-nowrap">
                    {formatTime(s.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-white font-semibold whitespace-nowrap">
                    {s.streamId}
                  </td>
                  <td className="px-4 py-3 text-guardian-muted">
                    #{s.trackId}
                  </td>
                  <td className="px-4 py-3">
                    {getThreatBadge(s.actionLabel)}
                  </td>
                  <td className="px-4 py-3 font-bold text-white whitespace-nowrap">
                    {(s.actionConfidence * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-guardian-muted mr-1.5">Seq #{s.bestFrameSeq}</span>
                    <span className="px-1.5 py-0.5 rounded bg-gray-800 text-white font-bold">
                      {(s.bestFrameScore * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-guardian-accent whitespace-nowrap">
                    {s.avgTotalLatencyMs.toFixed(1)} ms
                  </td>
                </tr>
              ))}
              {sequences.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-guardian-muted font-normal">
                    No sequence logs found in database.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
