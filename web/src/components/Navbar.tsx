import { useEffect, useRef, useState } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { Radar, Menu, X, ChevronDown } from 'lucide-react';
import { useHealth } from '../lib/useHealth';

interface Item { to: string; label: string; hint?: string; end?: boolean }

const primary: Item[] = [
  { to: '/', label: 'Briefing', end: true },
  { to: '/ops', label: 'Operations' },
  { to: '/cases', label: 'Cases' },
];

const groups: { label: string; items: Item[] }[] = [
  {
    label: 'Tools',
    items: [
      { to: '/sar-lab', label: 'SAR Lab', hint: 'Inspect real radar chips and run the detector' },
      { to: '/screening', label: 'Vessel screening', hint: 'Check OFAC and UN sanctions lists' },
    ],
  },
  {
    label: 'Reference',
    items: [
      { to: '/data', label: 'Data and provenance', hint: 'What is real, derived or synthetic' },
      { to: '/results', label: 'Results', hint: 'Measured model and workflow results' },
      { to: '/methodology', label: 'Methodology', hint: 'Provenance tags and legal basis' },
      { to: '/audit', label: 'Audit ledger', hint: 'Hash-chained record of actions' },
    ],
  },
];

const healthUi = {
  checking: { dot: 'bg-slate-500', text: 'Checking…' },
  online: { dot: 'bg-emerald-400', text: 'API online' },
  degraded: { dot: 'bg-amber-400', text: 'API degraded' },
  offline: { dot: 'bg-rose-500', text: 'API offline' },
} as const;

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm transition-colors ${isActive ? 'text-white bg-white/10' : 'text-slate-400 hover:text-white hover:bg-white/5'}`;

const Dropdown = ({ label, items }: { label: string; items: Item[] }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const loc = useLocation();
  const active = items.some((i) => loc.pathname.startsWith(i.to));

  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`flex items-center gap-1 rounded-md px-3 py-2 text-sm transition-colors ${active || open ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
      >
        {label}
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div role="menu" className="absolute left-0 top-full z-50 mt-2 w-72 rounded-xl border border-white/10 bg-[#0C1424] p-1.5 shadow-2xl">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} role="menuitem" className={({ isActive }) => `block rounded-lg px-3 py-2.5 ${isActive ? 'bg-white/10' : 'hover:bg-white/5'}`}>
              <div className="text-sm font-medium text-white">{i.label}</div>
              {i.hint && <div className="mt-0.5 text-xs text-slate-400">{i.hint}</div>}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
};

export const Navbar = () => {
  const [open, setOpen] = useState(false);
  const health = useHealth();
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);

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
          {primary.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkCls}>{l.label}</NavLink>
          ))}
          {groups.map((g) => <Dropdown key={g.label} label={g.label} items={g.items} />)}
        </nav>

        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-xs text-slate-400 lg:flex" title="Backend /readyz">
            <span className={`h-2 w-2 rounded-full ${healthUi[health].dot}`} />
            {healthUi[health].text}
          </span>
          <Link to="/ops" className="hidden rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 sm:inline-block">
            Open Operations
          </Link>
          <button className="rounded-md p-2 text-slate-300 hover:bg-white/10 md:hidden" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="max-h-[75dvh] overflow-y-auto border-t border-white/10 bg-[#0C1424] px-4 py-3 md:hidden" aria-label="Mobile">
          <div className="flex flex-col gap-1">
            {primary.map((l) => <NavLink key={l.to} to={l.to} end={l.end} className={linkCls}>{l.label}</NavLink>)}
            {groups.map((g) => (
              <div key={g.label} className="mt-3">
                <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-widest text-slate-500">{g.label}</div>
                {g.items.map((i) => <NavLink key={i.to} to={i.to} className={linkCls}>{i.label}</NavLink>)}
              </div>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
};
