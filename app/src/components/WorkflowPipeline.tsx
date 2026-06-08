import { motion } from 'framer-motion';
import {
  Database, BarChart4, Newspaper, Activity,
  ShieldAlert, Target, CheckCircle2,
} from 'lucide-react';
import type { PhaseStatus } from '../App';

const PIPE_NODES = [
  { id: 'prefetch', label: 'PREFETCH', icon: Database, cx: 300, cy: 40 },
  { id: 'data', label: 'MKT DATA', icon: BarChart4, cx: 110, cy: 135 },
  { id: 'news', label: 'NEWS SCAN', icon: Newspaper, cx: 300, cy: 135 },
  { id: 'analysis', label: 'TECHNICALS', icon: Activity, cx: 490, cy: 135 },
  { id: 'risk', label: 'RISK AGENT', icon: ShieldAlert, cx: 300, cy: 230 },
  { id: 'expert', label: 'EQUITY AI', icon: Target, cx: 300, cy: 320 },
  { id: 'complete', label: 'ASSEMBLE', icon: CheckCircle2, cx: 300, cy: 405 },
];

const PIPE_EDGES = [
  { from: 'prefetch', to: 'data' },
  { from: 'prefetch', to: 'news' },
  { from: 'prefetch', to: 'analysis' },
  { from: 'data', to: 'risk' },
  { from: 'news', to: 'risk' },
  { from: 'analysis', to: 'risk' },
  { from: 'risk', to: 'expert' },
  { from: 'expert', to: 'complete' },
];

const NW = 140, NH = 44, NR = 10;

function edgePath(from: typeof PIPE_NODES[0], to: typeof PIPE_NODES[0]): string {
  const x1 = from.cx, y1 = from.cy + NH / 2;
  const x2 = to.cx, y2 = to.cy - NH / 2;
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`;
  const midY = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`;
}

interface WorkflowPipelineProps {
  phases: Record<string, PhaseStatus>;
}

export default function WorkflowPipeline({ phases }: WorkflowPipelineProps) {
  const nodeMap = new Map(PIPE_NODES.map((n) => [n.id, n]));

  return (
    <div style={{ maxWidth: 640, margin: '0 auto' }}>
      <svg viewBox="0 0 600 440" style={{ width: '100%' }}>
        <defs>
          <filter id="node-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="edge-glow" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <linearGradient id="activeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d975" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#00a85a" stopOpacity={0.7} />
          </linearGradient>
        </defs>

        {/* Edges */}
        {PIPE_EDGES.map((e, i) => {
          const from = nodeMap.get(e.from)!;
          const to = nodeMap.get(e.to)!;
          const fromS = phases[e.from] || 'idle';
          const toS = phases[e.to] || 'idle';
          const active = fromS === 'done' || fromS === 'running';
          const flowing = fromS === 'done' && (toS === 'running' || toS === 'done');
          const d = edgePath(from, to);

          return (
            <g key={`e${i}`}>
              {/* Track */}
              <path d={d} fill="none" stroke="rgba(var(--border-rgb), 0.06)" strokeWidth={1.5} />

              {/* Active glow */}
              {active && (
                <path
                  d={d} fill="none"
                  stroke="rgba(0, 217, 117, 0.3)" strokeWidth={1}
                  filter="url(#edge-glow)"
                />
              )}

              {/* Flowing dash */}
              {flowing ? (
                <motion.path
                  d={d} fill="none" stroke="#00d975" strokeWidth={2}
                  strokeDasharray="6 9"
                  animate={{ strokeDashoffset: [0, -30] }}
                  transition={{ repeat: Infinity, duration: 0.65, ease: 'linear' }}
                />
              ) : active ? (
                <path d={d} fill="none" stroke="rgba(0, 217, 117, 0.5)" strokeWidth={1.5} />
              ) : null}
            </g>
          );
        })}

        {/* Nodes */}
        {PIPE_NODES.map((node) => {
          const status = phases[node.id] || 'idle';
          const x = node.cx - NW / 2;
          const y = node.cy - NH / 2;
          const isRunning = status === 'running';
          const isDone = status === 'done';
          const Icon = node.icon;

          return (
            <g key={node.id}>
              {/* Outer pulse ring when running */}
              {isRunning && (
                <motion.rect
                  x={x - 4} y={y - 4} width={NW + 8} height={NH + 8} rx={NR + 4}
                  fill="none" stroke="rgba(0, 217, 117, 0.2)" strokeWidth={1}
                  animate={{ opacity: [0.15, 0.7, 0.15] }}
                  transition={{ repeat: Infinity, duration: 1.3, ease: 'easeInOut' }}
                />
              )}

              {/* Node body */}
              {isRunning ? (
                <motion.rect
                  x={x} y={y} width={NW} height={NH} rx={NR}
                  fill="var(--base)"
                  stroke="#00d975" strokeWidth={1.5}
                  filter="url(#node-glow)"
                  animate={{ stroke: ['#00d975', '#4de89f', '#00d975'] }}
                  transition={{ repeat: Infinity, duration: 1.2 }}
                />
              ) : (
                <rect
                  x={x} y={y} width={NW} height={NH} rx={NR}
                  fill={isDone ? 'rgba(0, 217, 117, 0.05)' : 'var(--surface)'}
                  stroke={isDone ? 'rgba(0, 217, 117, 0.25)' : 'var(--border)'}
                  strokeWidth={1}
                />
              )}

              {/* Top-edge highlight */}
              <rect
                x={x + 4} y={y} width={NW - 8} height={1} rx={1}
                fill={isDone || isRunning ? 'rgba(0, 217, 117, 0.35)' : 'rgba(var(--border-rgb), 0.06)'}
              />

              {/* Icon */}
              <g transform={`translate(${x + 12}, ${node.cy})`}>
                <foreignObject x="-8" y="-8" width="16" height="16">
                  <div style={{ color: isRunning ? '#00d975' : isDone ? 'rgba(0,217,117,0.6)' : 'var(--text-muted)' }}>
                    <Icon size={14} />
                  </div>
                </foreignObject>
              </g>

              {/* Label */}
              <text
                x={node.cx + 8}
                y={node.cy + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontFamily="'JetBrains Mono', monospace"
                fontSize={10}
                fontWeight={600}
                letterSpacing="1.5"
                fill={
                  isRunning ? '#00d975'
                    : isDone ? 'rgba(0, 217, 117, 0.6)'
                      : 'var(--text-muted)'
                }
              >
                {node.label}
              </text>

              {/* Done checkmark */}
              {isDone && (
                <text
                  x={x + NW - 16} y={y + 14}
                  fill="#00d975" fontSize={12}
                  fontFamily="system-ui" fontWeight={700}
                >
                  ✓
                </text>
              )}

              {/* Running dot */}
              {isRunning && (
                <motion.circle
                  cx={x + NW - 14} cy={y + 14} r={3}
                  fill="#00d975"
                  animate={{ opacity: [1, 0.2, 1] }}
                  transition={{ repeat: Infinity, duration: 0.85 }}
                />
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
