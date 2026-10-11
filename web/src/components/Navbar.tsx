import { useState, useEffect } from 'react';
import { Radar, BookOpen, Database, Activity, Compass, Sliders } from 'lucide-react';

interface NavbarProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
}

export const Navbar = ({ currentRoute, onNavigate }: NavbarProps) => {
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: '/', label: 'Briefing', icon: Radar },
    { id: '/ops', label: 'Tactical Ops', icon: Compass },
    { id: '/audit', label: 'Audit Ledger', icon: Database },
    { id: '/methodology', label: 'Methodology', icon: BookOpen },
    { id: '/dev', label: 'Design System', icon: Sliders },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-cyan-500/20 bg-[#070B14]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div
          onClick={() => onNavigate('/')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="relative w-9 h-9 rounded-lg bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center overflow-hidden group-hover:border-cyan-400 transition-colors">
            <Radar className="w-5 h-5 text-cyan-400 group-hover:rotate-45 transition-transform duration-500" />
            <div className="absolute inset-0 bg-cyan-400/10 animate-ping rounded-lg pointer-events-none" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-lg tracking-tight text-white group-hover:text-cyan-300 transition-colors">
                DVD-MDA
              </span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-cyan-950 text-cyan-400 border border-cyan-500/30">
                v1.0
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">
              Maritime Domain Awareness
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#0C1424]/90 p-1 rounded-lg border border-slate-800">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentRoute === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium tracking-wide transition-all ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,229,255,0.2)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Telemetry Strip */}
        <div className="hidden lg:flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#0C1424] border border-slate-800">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300">{utcTime || '00:00:00 UTC'}</span>
          </div>

          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#0C1424] border border-slate-800 text-[11px]">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">7-NODE GRAPH</span>
            <span className="text-emerald-400 font-bold">READY</span>
          </div>

          <button
            onClick={() => onNavigate('/ops')}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs tracking-wider uppercase transition-all shadow-[0_0_20px_rgba(0,229,255,0.3)] hover:shadow-[0_0_30px_rgba(0,229,255,0.5)] active:scale-95"
          >
            Launch Console
          </button>
        </div>
      </div>
    </header>
  );
};
