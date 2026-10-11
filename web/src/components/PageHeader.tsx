import type { ReactNode } from 'react';

interface Props {
  eyebrow: string;
  title: string;
  lead?: string;
  actions?: ReactNode;
}

/** Consistent page title block used by every non-showcase page. */
export const PageHeader = ({ eyebrow, title, lead, actions }: Props) => (
  <header className="border-b border-white/10 bg-gradient-to-b from-[#0C1424] to-[#070B14] px-4 py-10 sm:px-6">
    <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-6">
      <div className="max-w-2xl">
        <p className="font-mono text-xs tracking-[0.2em] text-cyan-400">{eyebrow.toUpperCase()}</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">{title}</h1>
        {lead && <p className="mt-4 text-lg leading-relaxed text-slate-300">{lead}</p>}
      </div>
      {actions}
    </div>
  </header>
);

export const Card = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`rounded-2xl border border-white/10 bg-[#0C1424] p-6 ${className}`}>{children}</div>
);
