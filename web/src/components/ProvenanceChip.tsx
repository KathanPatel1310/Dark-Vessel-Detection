import { ShieldCheck, Cpu, Sparkles, Scale, AlertTriangle } from 'lucide-react';
import type { ProvenanceTag } from '../lib/api';

interface ProvenanceChipProps {
  provenance?: ProvenanceTag | string;
  source?: string;
  className?: string;
}

export const ProvenanceChip = ({
  provenance = 'DERIVED',
  source,
  className = '',
}: ProvenanceChipProps) => {
  const getBadgeConfig = (tag: string) => {
    switch (tag.toUpperCase()) {
      case 'REAL':
        return {
          label: 'REAL',
          icon: ShieldCheck,
          bg: 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30',
          desc: 'Empirical data parsed directly from official registries or sensor feeds',
        };
      case 'DERIVED':
        return {
          label: 'DERIVED',
          icon: Cpu,
          bg: 'bg-cyan-950/40 text-cyan-400 border-cyan-500/30',
          desc: 'Deterministically computed via physics, geometry, or feature pipelines',
        };
      case 'SYNTHETIC':
        return {
          label: 'TEST DATA',
          icon: Sparkles,
          bg: 'bg-purple-950/40 text-purple-400 border-purple-500/30 border-dashed',
          desc: 'Constructed test input, not an observation of a real event',
        };
      case 'HEURISTIC':
        return {
          label: 'HEURISTIC',
          icon: Scale,
          bg: 'bg-amber-950/40 text-amber-400 border-amber-500/30',
          desc: 'Expert-system probabilistic rules from maritime statutory conventions',
        };
      case 'UNAVAILABLE':
      default:
        return {
          label: 'UNAVAILABLE',
          icon: AlertTriangle,
          bg: 'bg-rose-950/40 text-rose-400 border-rose-500/30',
          desc: 'Telemetry feed offline or transponder broadcast missing',
        };
    }
  };

  const config = getBadgeConfig(provenance);
  const Icon = config.icon;

  return (
    <span
      title={source ? `${config.desc} • Source: ${source}` : config.desc}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono tracking-wider border uppercase cursor-help transition-colors ${config.bg} ${className}`}
    >
      <Icon className="w-3 h-3 shrink-0" />
      <span>{config.label}</span>
      {source && <span className="opacity-50 text-xs lowercase">• {source.split('/')[0]}</span>}
    </span>
  );
};
