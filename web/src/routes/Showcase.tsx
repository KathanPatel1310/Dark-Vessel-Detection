import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Satellite, Radar, Cpu, FileText, ArrowRight } from 'lucide-react';
import { ScrollFrameHero } from '../components/ScrollFrameHero';
import { ProvenanceChip } from '../components/ProvenanceChip';
import { useReveal } from '../lib/useReveal';
import type { PlatformMeta, ScenarioFixture, InventoryAsset } from '../lib/api';
import { fetchMeta, fetchScenarios, fetchInventory } from '../lib/api';

interface ShowcaseProps {
  onLaunchOps: (scenarioId?: string) => void;
}

const CHAPTERS = [
  { id: 'problem', label: 'The blind spot' },
  { id: 'how-it-works', label: 'How it works' },
  { id: 'agents', label: 'Agent workflow' },
  { id: 'legal', label: 'Legal basis' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'try', label: 'Try it' },
] as const;

const Section = ({
  id,
  index,
  eyebrow,
  title,
  lead,
  children,
}: {
  id: string;
  index: number;
  eyebrow: string;
  title: ReactNode;
  lead?: string;
  children?: ReactNode;
}) => (
  <section id={id} data-chapter className="scroll-mt-20 border-t border-white/5 px-6 py-24 sm:py-32">
    <div className="mx-auto max-w-6xl">
      <div className="reveal max-w-3xl">
        <p className="font-mono text-xs tracking-[0.2em] text-cyan-400">
          {String(index).padStart(2, '0')} — {eyebrow.toUpperCase()}
        </p>
        <h2 className="mt-4 font-display text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl">
          {title}
        </h2>
        {lead && <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">{lead}</p>}
      </div>
      {children && <div className="mt-14">{children}</div>}
    </div>
  </section>
);

const DOSSIER_SECTIONS = [
  'Executive assessment',
  'Situation and timeline',
  'Target identification',
  'Radar imagery evidence',
  'AIS analysis',
  'Geospatial and jurisdiction',
  'Sanctions screening',
  'Full feature appendix',
  'Risk assessment and counterfactuals',
  'Predictive forecast',
  'Agent workflow trace',
  'Human review and audit trail',
  'Legal basis',
  'Alternative hypotheses and limits',
  'Data lineage and provenance',
  'Integrity and reproducibility',
] as const;

const NODES = [
  ['Mission Controller', 'Defines the area and time window'],
  ['SAR–AIS Correlator', 'Matches the radar target to AIS reports'],
  ['Feature Engineer', 'Computes the engineered features'],
  ['Sanctions Screener', 'Checks OFAC and UN registries'],
  ['Forensic Assessor', 'Scores risk, projects the track'],
  ['Human Review', 'An analyst approves high-risk cases', true],
  ['Report Preparer', 'Writes the intelligence bulletin'],
] as const;

export const Showcase = ({ onLaunchOps }: ShowcaseProps) => {
  const [meta, setMeta] = useState<PlatformMeta | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioFixture[]>([]);
  const [active, setActive] = useState<string>('');
  const [apiError, setApiError] = useState(false);
  const [assets, setAssets] = useState<InventoryAsset[]>([]);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => setApiError(true));
    fetchScenarios().then(setScenarios).catch(() => setApiError(true));
    fetchInventory().then((i) => setAssets(i.assets)).catch(() => undefined);
  }, []);

  const inv = {
    chips: assets.find((a) => a.id === 'sar_chips')?.count ?? null,
    sanctions: assets.find((a) => a.id === 'sanctions_index')?.count ?? null,
    synthetic: assets.filter((a) => a.provenance === 'SYNTHETIC').reduce((n, a) => n + (a.count ?? 0), 0) || null,
  };

  useReveal([scenarios.length, meta, assets.length]);

  // Highlight the chapter currently in view
  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>('[data-chapter]');
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: '-45% 0px -50% 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });

  return (
    <div className="w-full">
      <ScrollFrameHero onLaunch={() => onLaunchOps('SCN-DARK-001')} />

      {/* Chapter indicator */}
      <nav aria-label="Sections" className="fixed right-5 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-3 xl:flex">
        {CHAPTERS.map((c) => (
          <button
            key={c.id}
            onClick={() => go(c.id)}
            aria-label={c.label}
            aria-current={active === c.id}
            className="group flex items-center justify-end gap-3"
          >
            <span
              className={`text-xs transition-opacity ${
                active === c.id ? 'text-cyan-300 opacity-100' : 'text-slate-400 opacity-0 group-hover:opacity-100'
              }`}
            >
              {c.label}
            </span>
            <span
              className={`block rounded-full transition-all ${
                active === c.id ? 'h-2.5 w-2.5 bg-cyan-400' : 'h-2 w-2 bg-slate-600 group-hover:bg-slate-400'
              }`}
            />
          </button>
        ))}
      </nav>

      <Section
        id="problem"
        index={1}
        eyebrow="The blind spot"
        title={
          <>
            Ships can vanish from AIS. They can’t vanish from <span className="accent-word">radar</span>.
          </>
        }
        lead="AIS was designed for collision avoidance. Vessels that avoid sanctions or inspection simply switch it off, so tracking feeds show an empty ocean. Satellite radar still sees the hull."
      >
        <div className="grid gap-5 md:grid-cols-3">
          {[
            { icon: Satellite, t: 'Sentinel-1 SAR', d: 'C-band radar images the sea day and night, through cloud.' },
            { icon: Radar, t: 'Unmatched targets', d: 'Each radar detection is compared with AIS reports in space and time.' },
            { icon: FileText, t: 'A hypothesis, not a verdict', d: 'The output is a probability with evidence, reviewed by a person.' },
          ].map(({ icon: Icon, t, d }) => (
            <div key={t} className="reveal rounded-2xl border border-white/10 bg-[#0C1424] p-7">
              <Icon className="h-6 w-6 text-cyan-400" />
              <h3 className="mt-5 font-display text-xl font-semibold text-white">{t}</h3>
              <p className="mt-2 leading-relaxed text-slate-400">{d}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="how-it-works"
        index={2}
        eyebrow="How it works"
        title={
          <>
            From pixels to <span className="accent-word">evidence</span> in four steps.
          </>
        }
        lead={
          meta
            ? `Every decision is built on ${meta.feature_count} engineered features across five domains: radar, AIS, geography, history and fusion.`
            : 'Every decision is built on engineered features across five domains: radar, AIS, geography, history and fusion.'
        }
      >
        <ol className="grid gap-5 md:grid-cols-4">
          {[
            ['Detect', 'A YOLO-based detector finds ships in the radar chip and measures length, beam and heading.'],
            ['Correlate', 'Each detection is matched to AIS within a distance and time gate.'],
            ['Assess', 'Features, sanctions screening and EEZ position produce a risk score.'],
            ['Report', 'A structured bulletin cites the relevant maritime law and recommends actions.'],
          ].map(([t, d], i) => (
            <li key={t} className="reveal rounded-2xl border border-white/10 bg-[#0C1424] p-6" style={{ transitionDelay: `${i * 80}ms` }}>
              <span className="font-stat text-sm text-cyan-400">0{i + 1}</span>
              <h3 className="mt-3 font-display text-xl font-semibold text-white">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{d}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 text-sm text-slate-500">
          Feature definitions and formulas are listed on the{' '}
          <Link to="/methodology" className="text-cyan-400 underline underline-offset-4">
            Methodology page
          </Link>
          .
        </p>
      </Section>

      <Section
        id="agents"
        index={3}
        eyebrow="Agent workflow"
        title={
          <>
            Seven nodes, one <span className="accent-word">accountable</span> path.
          </>
        }
        lead="A LangGraph state machine runs the investigation. When risk is high, execution pauses at a human checkpoint before any report is issued."
      >
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {NODES.map(([name, desc, hitl], i) => (
            <li
              key={name}
              className={`reveal rounded-xl border p-5 ${
                hitl ? 'border-amber-500/40 bg-amber-950/20' : 'border-white/10 bg-[#0C1424]'
              }`}
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              <div className="flex items-center justify-between">
                <span className={`font-stat text-sm ${hitl ? 'text-amber-400' : 'text-cyan-400'}`}>0{i + 1}</span>
                {hitl && <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs text-amber-300">Conditional</span>}
              </div>
              <h3 className="mt-3 font-display text-lg font-semibold text-white">{name}</h3>
              <p className="mt-1 text-sm text-slate-400">{desc}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="legal"
        index={4}
        eyebrow="Legal basis"
        title={
          <>
            Every finding cites <span className="accent-word">real law</span>.
          </>
        }
        lead="Citations come from a fixed catalogue, never from a language model, so the legal text is always accurate."
      >
        <div className="grid gap-4 md:grid-cols-2">
          {(meta?.citation_catalog ?? []).map((c) => (
            <article key={c.id} className="reveal rounded-2xl border border-white/10 bg-[#0C1424] p-6">
              <h3 className="font-display text-lg font-semibold text-cyan-300">{c.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{c.scope}</p>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{c.statute}</p>
              {c.link && (
                <a href={c.link} target="_blank" rel="noreferrer" className="mt-4 inline-block text-sm text-cyan-400 underline underline-offset-4">
                  Read the source
                </a>
              )}
            </article>
          ))}
          {!meta && <p className="text-slate-500">{apiError ? 'Start the API to load the citation catalogue.' : 'Loading…'}</p>}
        </div>
      </Section>

      <Section
        id="evidence"
        index={5}
        eyebrow="Evidence"
        title={
          <>
            Every claim traces back to <span className="accent-word">data you can open</span>.
          </>
        }
        lead="Nothing on screen is decoration. The platform shows exactly which inputs are real, which are computed from real data, and which are synthetic test fixtures — and every case can be exported as a full PDF dossier."
      >
        <div className="grid gap-5 lg:grid-cols-5">
          <div className="reveal rounded-2xl border border-white/10 bg-[#0C1424] p-7 lg:col-span-2">
            <h3 className="font-display text-xl font-semibold text-white">What the platform is built on</h3>
            <dl className="mt-5 space-y-4">
              {[
                ['REAL', inv.chips, 'Sentinel-1 radar chips with the vessel’s own AIS'],
                ['REAL', inv.sanctions, 'sanctioned vessels indexed from OFAC and UN lists'],
                ['DERIVED', meta?.feature_count ?? null, 'engineered features computed per detection'],
                ['SYNTHETIC', inv.synthetic, 'test fixtures and generated tables, always labelled'],
              ].map(([tag, n, label]) => (
                <div key={String(label)} className="flex items-baseline gap-4">
                  <dt className="w-20 shrink-0 text-right font-stat text-3xl font-semibold text-white">{n == null ? '—' : Number(n).toLocaleString()}</dt>
                  <dd className="text-sm leading-snug text-slate-300">
                    <span className="mr-2 align-middle"><ProvenanceChip provenance={String(tag)} /></span>
                    {label}
                  </dd>
                </div>
              ))}
            </dl>
            <Link to="/data" className="mt-6 inline-flex items-center gap-2 text-sm text-cyan-300 underline underline-offset-4">
              Browse the full data inventory <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="reveal rounded-2xl border border-white/10 bg-[#0C1424] p-7 lg:col-span-3">
            <h3 className="font-display text-xl font-semibold text-white">What’s inside an exported dossier</h3>
            <p className="mt-1 text-sm text-slate-400">One PDF per case — roughly 19 pages with embedded radar imagery, maps and tables.</p>
            <ol className="mt-5 grid gap-x-6 gap-y-1.5 text-sm text-slate-300 sm:grid-cols-2">
              {DOSSIER_SECTIONS.map((t, i) => (
                <li key={t} className="flex gap-3">
                  <span className="w-5 shrink-0 text-right font-mono text-xs leading-6 text-cyan-400">{i + 1}</span>
                  {t}
                </li>
              ))}
            </ol>
            <button
              onClick={() => onLaunchOps()}
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300"
            >
              Run a case and export one <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
        <p className="mt-6 text-sm text-slate-500">
          Honest caveats live where they matter — in every exported dossier (§14) and on the{' '}
          <Link to="/data" className="text-cyan-400 underline underline-offset-4">Data</Link> page.
        </p>
      </Section>

      <Section
        id="try"
        index={6}
        eyebrow="Try it"
        title={
          <>
            Pick a scenario and <span className="accent-word">investigate</span>.
          </>
        }
        lead="Each scenario runs through the real Python pipeline in the Operations console."
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {scenarios.map((s) => (
            <button
              key={s.scenario_id}
              onClick={() => onLaunchOps(s.scenario_id)}
              className="reveal group rounded-2xl border border-white/10 bg-[#0C1424] p-6 text-left transition hover:-translate-y-1 hover:border-cyan-500/50"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-cyan-400">{s.scenario_id}</span>
                <span className="text-xs text-slate-500">Expected: {s.expected_threat_tier}</span>
              </div>
              <h3 className="mt-3 font-display text-lg font-semibold text-white">{s.scenario_name}</h3>
              <p className="mt-2 line-clamp-3 text-sm text-slate-400">{s.description}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm text-cyan-300 transition group-hover:gap-2">
                Open in console <ArrowRight className="h-4 w-4" />
              </span>
            </button>
          ))}
          {!scenarios.length && (
            <p className="text-slate-500">{apiError ? 'Start the API (uvicorn src.api.server:app) to load scenarios.' : 'Loading…'}</p>
          )}
        </div>
      </Section>

      <footer className="border-t border-white/10 px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 text-sm text-slate-500 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-slate-300">
            <Cpu className="h-4 w-4 text-cyan-400" /> Dark Vessel MDA — academic research prototype
          </div>
          <p className="max-w-md">Not for operational targeting. Data: Copernicus Sentinel-1, OFAC SDN, UN Consolidated List.</p>
          <div className="flex gap-5">
            <Link to="/methodology" className="hover:text-white">Methodology</Link>
            <Link to="/audit" className="hover:text-white">Audit</Link>
            <a href="https://github.com/KathanPatel1310/Dark-Vessel-Detection" target="_blank" rel="noreferrer" className="hover:text-white">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
