import { useEffect, useState } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { Radar, Menu, X } from 'lucide-react';
import { useHealth } from '../lib/useHealth';

const links = [
  { to: '/', label: 'Briefing', end: true },
  { to: '/ops', label: 'Operations', end: false },
  { to: '/audit', label: 'Audit', end: false },
  { to: '/methodology', label: 'Methodology', end: false },
];

const healthUi = {
  checking: { dot: 'bg-slate-500', text: 'Checking…' },
  online: { dot: 'bg-emerald-400', text: 'API online' },
  degraded: { dot: 'bg-amber-400', text: 'API degraded' },
  offline: { dot: 'bg-rose-500', text: 'API offline' },
} as const;

export const Navbar = () => {
  const [open, setOpen] = useState(false);
  const health = useHealth();
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-md text-sm transition-colors ${
      isActive ? 'text-white bg-white/10' : 'text-slate-400 hover:text-white hover:bg-white/5'
    }`;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#070B14]/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/60">
            <Radar className="h-5 w-5 text-cyan-400" />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-white">
            Dark Vessel <span className="text-cyan-400">MDA</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkCls}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-xs text-slate-400 lg:flex" title="Backend /readyz">
            <span className={`h-2 w-2 rounded-full ${healthUi[health].dot}`} />
            {healthUi[health].text}
          </span>
          <Link
            to="/ops"
            className="hidden rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 sm:inline-block"
          >
            Open Operations
          </Link>
          <button
            className="rounded-md p-2 text-slate-300 hover:bg-white/10 md:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="border-t border-white/10 bg-[#0C1424] px-4 py-3 md:hidden" aria-label="Mobile">
          <div className="flex flex-col gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className={linkCls}>
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
};
