import { useState, useEffect, useRef, useMemo } from 'react';
import { Play, ShieldAlert, FileText, ChevronUp, ChevronDown, RefreshCw, Check, X, Search, Satellite } from 'lucide-react';
import { ProvenanceChip } from '../components/ProvenanceChip';
import { TacticalMap } from '../components/TacticalMap';
import type { ScenarioFixture, InvestigationResult, RealCaseRow, PlatformMeta } from '../lib/api';
import {
  fetchScenarios,
  fetchRealCases,
  fetchRealCase,
  fetchMeta,
  runInvestigation,
  submitHITLDecision,
  downloadReportPdf,
} from '../lib/api';

interface OperationsProps {
  initialScenarioId?: string;
}

type Tab = 'map' | 'sar' | 'fusion';
type Band = 'vv' | 'vh' | 'rgb';
type Disposition = 'APPROVED' | 'REJECTED' | 'ESCALATED';

const statusColor: Record<string, string> = {
  SUCCESS: 'text-emerald-400',
  APPROVED: 'text-emerald-400',
  DEGRADED: 'text-amber-400',
  SKIPPED: 'text-slate-500',
  FAILED: 'text-rose-400',
  OVERRIDDEN: 'text-amber-400',
};

const haversineKm = (a: [number, number], b: [number, number]) => {
  const R = 6371;
  const toR = (d: number) => (d * Math.PI) / 180;
  const dLat = toR(b[0] - a[0]);
  const dLon = toR(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a[0])) * Math.cos(toR(b[0])) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
};

export const Operations = ({ initialScenarioId = 'SCN-DARK-001' }: OperationsProps) => {
  const [scenarios, setScenarios] = useState<ScenarioFixture[]>([]);
  const [realCases, setRealCases] = useState<RealCaseRow[]>([]);
  const [realQuery, setRealQuery] = useState('');
  const [realShown, setRealShown] = useState(30);
  const [group, setGroup] = useState<'real' | 'synthetic'>(initialScenarioId.startsWith('REAL-') ? 'real' : 'synthetic');
  const [selected, setSelected] = useState<ScenarioFixture | null>(null);
  const [loadingCase, setLoadingCase] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [meta, setMeta] = useState<PlatformMeta | null>(null);

  const [cutAIS, setCutAIS] = useState(false);
  const [offlineSanctions, setOfflineSanctions] = useState(false);

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [revealed, setRevealed] = useState(0);
  const [tab, setTab] = useState<Tab>('map');
  const [band, setBand] = useState<Band>('vv');
  const [drawerOpen, setDrawerOpen] = useState(true);

  const [exporting, setExporting] = useState(false);
  const [useLlm, setUseLlm] = useState(false);
  const [exportNote, setExportNote] = useState<string | null>(null);

  const [showHITL, setShowHITL] = useState(false);
  const [hitlDone, setHitlDone] = useState(false);
  const [disposition, setDisposition] = useState<Disposition>('APPROVED');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const chipRef = useRef<HTMLCanvasElement | null>(null);
  const selectedId = selected?.scenario_id ?? initialScenarioId;

  const reset = () => {
    setResult(null);
    setRevealed(0);
    setShowHITL(false);
    setHitlDone(false);
    setRunError(null);
    setExportNote(null);
  };

  const loadReal = async (chipId: string) => {
    setLoadingCase(true);
    setLoadError(null);
    reset();
    try {
      setSelected(await fetchRealCase(chipId));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Could not load the real case');
    } finally {
      setLoadingCase(false);
    }
  };

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => undefined);
    Promise.all([fetchScenarios(), fetchRealCases().catch(() => ({ cases: [] as RealCaseRow[] }))])
      .then(([list, real]) => {
        setScenarios(list);
        setRealCases(real.cases);
        if (initialScenarioId.startsWith('REAL-')) {
          loadReal(initialScenarioId.replace('REAL-', ''));
        } else {
          setSelected(list.find((s) => s.scenario_id === initialScenarioId) ?? list[0] ?? null);
        }
      })
      .catch((e) => setLoadError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialScenarioId]);

  const selectScenario = (s: ScenarioFixture) => {
    setSelected(s);
    reset();
  };

  // Reveal trace steps one at a time so the 7-node workflow reads as it executes
  useEffect(() => {
    if (!result) return;
    if (revealed >= result.execution_trace.length) {
      if (result.human_in_the_loop_required && !hitlDone) setShowHITL(true);
      return;
    }
    const t = setTimeout(() => setRevealed((n) => n + 1), 280);
    return () => clearTimeout(t);
  }, [result, revealed, hitlDone]);

  useEffect(() => {
    if (!showHITL) return;
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setShowHITL(false);
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [showHITL]);

  const run = async () => {
    if (!selected) return;
    reset();
    setIsRunning(true);
    const aisOff = cutAIS || selected.scenario_type === 'DEGRADED_EVIDENCE';
    try {
      const res = await runInvestigation({
        mission_id: `OPS-${selected.scenario_id.slice(0, 24)}-${Date.now().toString().slice(-4)}`,
        sar_detection: selected.sar_detection,
        matched_ais: cutAIS ? null : selected.ais_observation,
        historical_gaps: selected.historical_gaps ?? [],
        simulate_ais_offline: aisOff,
        simulate_sanctions_offline: offlineSanctions || selected.scenario_type === 'DEGRADED_EVIDENCE',
        chip_id: selected.chip_id,
        scenario_id: selected.scenario_id,
        ground_truth: selected.ground_truth,
        ground_truth_ais: selected.ground_truth_ais,
        all_detections: selected.all_detections,
        provenance: cutAIS && selected.provenance ? { ...selected.provenance, ais: 'UNAVAILABLE' } : selected.provenance,
      });
      setResult(res);
      setDrawerOpen(true);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'Investigation failed');
    } finally {
      setIsRunning(false);
    }
  };

  const submitHITL = async () => {
    if (!result?.session_id || notes.trim().length < 10) return;
    setSubmitting(true);
    try {
      await submitHITLDecision({ session_id: result.session_id, analyst_disposition: disposition, audit_notes: notes });
      setHitlDone(true);
      setShowHITL(false);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'HITL submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const exportReport = async () => {
    const rid = result?.final_report?.report_id;
    if (!rid) return;
    setExporting(true);
    setExportNote(null);
    try {
      const { narrative } = await downloadReportPdf(rid, useLlm);
      setExportNote(narrative === 'LLM_VERIFIED' ? 'Downloaded · narrative drafted by Qwen and verified.' : 'Downloaded · rule-generated narrative.');
    } catch (e) {
      setExportNote(e instanceof Error ? `Export failed: ${e.message}` : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  // SAR schematic (only for test scenarios, which have no raw chip)
  useEffect(() => {
    const canvas = chipRef.current;
    if (!canvas || !selected || tab !== 'sar' || selected.chip_id) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const det = selected.sar_detection;
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = '#0a1220';
    ctx.fillRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h / 2;
    const len = Math.max(30, Math.min(w * 0.6, (det.length_m / 300) * w * 0.6));
    const beam = Math.max(10, len / Math.max(det.aspect_ratio || 5, 1.5));
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(((det.heading_deg ?? 0) * Math.PI) / 180 - Math.PI / 2);
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = 'rgba(245,158,11,0.6)';
    ctx.strokeRect(-len / 2 - 15, -beam / 2 - 15, len + 30, beam + 30);
    ctx.fillStyle = 'rgba(0,229,255,0.85)';
    ctx.fillRect(-len / 2, -beam / 2, len, beam);
    ctx.setLineDash([]);
    ctx.strokeStyle = '#fff';
    ctx.strokeRect(-len / 2, -beam / 2, len, beam);
    ctx.restore();
    ctx.font = '12px "JetBrains Mono Variable", monospace';
    ctx.fillStyle = '#00E5FF';
    ctx.fillText(`L ${det.length_m.toFixed(0)} m · B ${det.width_m.toFixed(0)} m · conf ${(det.confidence * 100).toFixed(0)}%`, 14, 24);
  }, [selected, tab]);

  const filteredReal = useMemo(() => {
    const q = realQuery.trim().toLowerCase();
    return realCases.filter((r) => !q || r.vessel_name.toLowerCase().includes(q) || r.mmsi.includes(q) || r.vessel_type.toLowerCase().includes(q));
  }, [realCases, realQuery]);

  const steps = result?.execution_trace.slice(0, revealed) ?? [];
  const traceDone = !!result && revealed >= result.execution_trace.length;
  const report = result?.final_report ?? null;
  const detection = selected?.sar_detection;
  const aisUsed = cutAIS ? null : selected?.ais_observation ?? null;
  const spatialKm =
    detection && aisUsed ? haversineKm([detection.latitude, detection.longitude], [aisUsed.latitude, aisUsed.longitude]) : null;
  const isReal = !!selected?.chip_id;
  const llmOk = meta?.llm?.available ?? false;
  const outOfCoverage = result?.geo_context && result.geo_context.in_coverage === false;

  const stepState = (n: 1 | 2 | 3) =>
    n === 1 ? (selected ? 'done' : 'active') : n === 2 ? (result ? 'done' : selected ? 'active' : 'idle') : traceDone ? 'active' : 'idle';

  const ExportButton = ({ className = '' }: { className?: string }) => (
    <button
      onClick={exportReport}
      disabled={!report || !traceDone || exporting}
      title={report ? 'Download the full PDF dossier' : 'Run an investigation first'}
      className={`inline-flex items-center gap-2 rounded-md bg-cyan-400 px-3 py-1.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {exporting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
      {exporting ? 'Building report…' : 'Export report'}
    </button>
  );

  return (
    <div className="flex h-[calc(100dvh-4rem)] flex-col overflow-hidden bg-[#070B14]">
      {/* Sub-bar */}
      <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 bg-[#0C1424] px-4 py-2 text-sm">
        <div className="flex min-w-0 items-center gap-3">
          <span className="font-mono text-cyan-400">{selectedId.length > 26 ? selectedId.slice(0, 26) + '…' : selectedId}</span>
          <span className="hidden truncate text-slate-300 sm:inline">{selected?.scenario_name}</span>
          <ProvenanceChip provenance={isReal ? 'REAL' : selected?.provenance?.radar ?? 'SYNTHETIC'} />
        </div>
        <div className="flex items-center gap-3">
          <label
            className={`hidden items-center gap-2 text-xs sm:flex ${llmOk ? 'text-slate-300' : 'text-slate-600'}`}
            title={llmOk ? 'Let the fine-tuned Qwen 2.5 draft the summary (slower). Output is verified against the evidence.' : `Qwen files incomplete: ${meta?.llm?.missing.join(', ') ?? 'unknown'}`}
          >
            <input type="checkbox" disabled={!llmOk} checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="accent-cyan-400" />
            AI-drafted summary
          </label>
          <ExportButton />
        </div>
      </div>
      {exportNote && (
        <div className="shrink-0 border-b border-white/10 bg-cyan-950/30 px-4 py-1.5 text-xs text-cyan-200" role="status">
          {exportNote}
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[330px_1fr_360px]">
        {/* LEFT */}
        <aside className="flex min-h-0 flex-col gap-5 overflow-y-auto border-b border-white/10 p-4 lg:border-b-0 lg:border-r">
          <ol className="flex items-center gap-2 text-xs">
            {['Select', 'Run', 'Review'].map((label, i) => {
              const s = stepState((i + 1) as 1 | 2 | 3);
              return (
                <li key={label} className="flex flex-1 items-center gap-2">
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold ${
                      s === 'done' ? 'border-cyan-400 bg-cyan-400 text-slate-950' : s === 'active' ? 'border-cyan-400 text-cyan-300' : 'border-slate-700 text-slate-600'
                    }`}
                  >
                    {s === 'done' ? <Check className="h-3.5 w-3.5" /> : i + 1}
                  </span>
                  <span className={s === 'idle' ? 'text-slate-600' : 'text-slate-300'}>{label}</span>
                </li>
              );
            })}
          </ol>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-white">1. Choose a case</h2>
            <div className="mb-3 grid grid-cols-2 gap-1 rounded-lg bg-[#0C1424] p-1 text-xs" role="tablist">
              {([['real', `Real Sentinel-1 (${realCases.length})`], ['synthetic', `Test scenarios (${scenarios.length})`]] as const).map(([k, label]) => (
                <button
                  key={k}
                  role="tab"
                  aria-selected={group === k}
                  onClick={() => setGroup(k)}
                  className={`rounded-md px-2 py-1.5 transition ${group === k ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:text-white'}`}
                >
                  {label}
                </button>
              ))}
            </div>
            {loadError && <p className="mb-2 text-sm text-rose-400">{loadError}</p>}

            {group === 'real' ? (
              <div>
                <p className="mb-2 text-xs leading-relaxed text-slate-400">
                  Real radar chips with the vessel’s own AIS. Use <em>Cut AIS</em> to turn one into a dark-vessel test.
                </p>
                <div className="relative mb-2">
                  <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    value={realQuery}
                    onChange={(e) => { setRealQuery(e.target.value); setRealShown(30); }}
                    placeholder="Search name, MMSI, type…"
                    aria-label="Search real cases"
                    className="w-full rounded-lg border border-white/10 bg-[#0C1424] py-2 pl-8 pr-3 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  />
                </div>
                <div className="space-y-1.5">
                  {filteredReal.slice(0, realShown).map((r) => (
                    <button
                      key={r.chip_id}
                      onClick={() => loadReal(r.chip_id)}
                      aria-pressed={selected?.chip_id === r.chip_id}
                      className={`w-full rounded-lg border p-2.5 text-left text-sm transition ${
                        selected?.chip_id === r.chip_id ? 'border-cyan-500/60 bg-cyan-950/30' : 'border-white/10 bg-[#0C1424] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-medium text-white">{r.vessel_name || 'Unnamed'}</span>
                        <span className="shrink-0 text-xs text-slate-500">{r.true_length_m.toFixed(0)} m</span>
                      </div>
                      <div className="mt-0.5 text-xs text-slate-400">{r.vessel_type} · {r.acq_time.slice(0, 10)}</div>
                    </button>
                  ))}
                  {filteredReal.length === 0 && <p className="text-sm text-slate-500">No real cases match.</p>}
                  {filteredReal.length > realShown && (
                    <button onClick={() => setRealShown((n) => n + 30)} className="w-full rounded-lg border border-dashed border-white/15 py-2 text-xs text-slate-400 hover:text-white">
                      Show more ({filteredReal.length - realShown})
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs leading-relaxed text-slate-400">Constructed inputs that exercise each decision path of the software. They are not observations of real events.</p>
                {scenarios.map((s) => (
                  <button
                    key={s.scenario_id}
                    onClick={() => selectScenario(s)}
                    aria-pressed={s.scenario_id === selected?.scenario_id}
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      s.scenario_id === selected?.scenario_id ? 'border-cyan-500/60 bg-cyan-950/30' : 'border-white/10 bg-[#0C1424] hover:border-white/20'
                    }`}
                  >
                    <div className="text-sm font-medium text-white">{s.scenario_name}</div>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{s.description}</p>
                  </button>
                ))}
              </div>
            )}
            {loadingCase && <p className="mt-2 flex items-center gap-2 text-sm text-slate-400"><RefreshCw className="h-4 w-4 animate-spin" /> Running detector on the chip…</p>}
          </section>

          <section className="rounded-xl border border-white/10 bg-[#0C1424] p-4">
            <h2 className="text-sm font-semibold text-white">Degrade the evidence</h2>
            <p className="mt-1 text-xs text-slate-400">See how the assessment changes when data goes missing.</p>
            <label className="mt-3 flex cursor-pointer items-center justify-between gap-3 text-sm text-slate-200">
              Cut AIS feed
              <input type="checkbox" checked={cutAIS} onChange={(e) => { setCutAIS(e.target.checked); reset(); }} className="h-4 w-4 accent-amber-400" />
            </label>
            <label className="mt-3 flex cursor-pointer items-center justify-between gap-3 text-sm text-slate-200">
              Sanctions registry offline
              <input type="checkbox" checked={offlineSanctions} onChange={(e) => { setOfflineSanctions(e.target.checked); reset(); }} className="h-4 w-4 accent-amber-400" />
            </label>
            {isReal && cutAIS && <p className="mt-3 text-xs text-amber-300">Counterfactual: the vessel’s real AIS is hidden. This is a test, not an observed evasion.</p>}
          </section>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-white">2. Run the investigation</h2>
            <button
              onClick={run}
              disabled={isRunning || !selected || loadingCase}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-400 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50"
            >
              {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-slate-950" />}
              {isRunning ? 'Running agents…' : 'Run investigation'}
            </button>
            {runError && <p className="mt-2 text-sm text-rose-400">{runError}</p>}
          </section>
        </aside>

        {/* CENTER */}
        <main className="flex min-h-[360px] min-w-0 flex-col border-b border-white/10 lg:border-b-0 lg:border-r">
          <div role="tablist" className="flex shrink-0 gap-1 border-b border-white/10 bg-[#0C1424]/60 px-3 py-2 text-sm">
            {([['map', 'Map'], ['sar', 'SAR target'], ['fusion', 'Evidence']] as [Tab, string][]).map(([k, label]) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`rounded-md px-3 py-1.5 transition ${tab === k ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:text-white'}`}>
                {label}
              </button>
            ))}
          </div>

          <div className="relative min-h-0 flex-1">
            {tab === 'map' && (
              <>
                <TacticalMap detection={detection} ais={aisUsed} waypoints={result?.forecast?.extrapolated_waypoints} />
                {outOfCoverage && (
                  <div className="absolute left-3 top-3 z-[500] max-w-xs rounded-lg border border-amber-500/40 bg-[#0C1424]/95 p-3 text-xs text-amber-200">
                    This position is outside the bundled Arabian Sea EEZ/STS dataset, so no jurisdiction or corridor reasoning was applied.
                  </div>
                )}
              </>
            )}
            {tab === 'sar' && selected && (
              <div className="flex h-full flex-col items-center gap-3 overflow-y-auto p-4">
                {isReal ? (
                  <>
                    <div className="flex gap-1 rounded-lg bg-[#0C1424] p-1 text-xs" role="tablist">
                      {(['vv', 'vh', 'rgb'] as Band[]).map((b) => (
                        <button key={b} role="tab" aria-selected={band === b} onClick={() => setBand(b)} className={`rounded-md px-3 py-1.5 uppercase ${band === b ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:text-white'}`}>
                          {b === 'rgb' ? 'Composite' : b}
                        </button>
                      ))}
                    </div>
                    <img
                      src={`/api/chips/${encodeURIComponent(selected.chip_id!)}/image?band=${band}`}
                      alt={`Real Sentinel-1 ${band.toUpperCase()} chip with detector boxes`}
                      className="max-h-[calc(100%-5rem)] max-w-full rounded-xl border border-cyan-500/30 [image-rendering:pixelated]"
                    />
                    <p className="flex items-center gap-2 text-center text-xs text-slate-400">
                      <Satellite className="h-3.5 w-3.5 text-cyan-400" /> Real Sentinel-1 chip · cyan box = target · amber = other detections
                    </p>
                  </>
                ) : (
                  <>
                    <canvas ref={chipRef} width={480} height={340} className="max-w-full rounded-xl border border-cyan-500/30" />
                    <p className="max-w-md text-center text-xs text-slate-500">Test scenario — schematic from the stated dimensions, not radar imagery.</p>
                  </>
                )}
              </div>
            )}
            {tab === 'fusion' && detection && (
              <div className="h-full overflow-y-auto p-6">
                <h2 className="text-sm font-semibold text-white">SAR ↔ AIS evidence</h2>
                <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                  {[
                    ['AIS match', aisUsed ? `${aisUsed.vessel_name ?? aisUsed.mmsi}` : 'None — unmatched detection'],
                    ['Distance SAR ↔ AIS', spatialKm != null ? `${spatialKm.toFixed(2)} km` : '—'],
                    ['Radar length / beam', `${detection.length_m.toFixed(0)} m / ${detection.width_m.toFixed(0)} m`],
                    ...(selected?.ground_truth ? [['True length (vessel’s AIS)', `${selected.ground_truth.length_m.toFixed(0)} m`]] : []),
                    ['Detector confidence', `${(detection.confidence * 100).toFixed(0)}%`],
                    ['Dark-vessel hypothesis', result ? `${(result.risk_assessment.dark_vessel_probability * 100).toFixed(0)}% — ${result.risk_assessment.dark_vessel_classification}` : 'Run an investigation'],
                    ['Distance to coast', result?.geo_context ? (result.geo_context.in_coverage === false ? 'n/a (outside dataset)' : `${result.geo_context.distance_to_coast_km.toFixed(0)} km`) : '—'],
                  ].map(([k, v]) => (
                    <div key={k} className="rounded-xl border border-white/10 bg-[#0C1424] p-4">
                      <dt className="text-xs text-slate-500">{k}</dt>
                      <dd className="mt-1 font-medium text-white">{v}</dd>
                    </div>
                  ))}
                </dl>
                {result?.risk_assessment.risk_factors?.length ? (
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold text-white">Risk factors</h3>
                    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-300">
                      {result.risk_assessment.risk_factors.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </main>

        {/* RIGHT */}
        <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto p-4">
          <h2 className="text-sm font-semibold text-white">Agent trace</h2>
          {!result && !isRunning && (
            <p className="rounded-xl border border-dashed border-white/15 p-5 text-sm text-slate-400">
              Choose a case and press <strong className="text-slate-200">Run investigation</strong>. Each agent node appears here as it executes.
            </p>
          )}
          {isRunning && <p className="text-sm text-slate-400">Executing LangGraph workflow…</p>}

          <ol className="space-y-2">
            {steps.map((s) => (
              <li key={s.step_number} className="rounded-lg border border-white/10 bg-[#0C1424] p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-white">{s.step_number}. {s.agent_name}</span>
                  <span className={`text-xs font-semibold ${statusColor[s.status] ?? 'text-slate-400'}`}>{s.status}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{s.notes || s.action_taken}</p>
                {s.latency_ms != null && <p className="mt-1 font-mono text-[11px] text-slate-500">{s.latency_ms.toFixed(1)} ms</p>}
              </li>
            ))}
          </ol>

          {traceDone && result.degradation_notes.length > 0 && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200">
              <p className="mb-1 font-semibold">Degraded evidence</p>
              <ul className="list-inside list-disc space-y-0.5">{result.degradation_notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
            </div>
          )}

          {traceDone && result.human_in_the_loop_required && (
            <div className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-4 text-sm">
              <div className="flex items-center gap-2 font-semibold text-amber-300">
                <ShieldAlert className="h-4 w-4" /> {hitlDone ? 'Review recorded' : 'Human review required'}
              </div>
              {!hitlDone && (
                <button onClick={() => setShowHITL(true)} className="mt-3 w-full rounded-lg bg-amber-500 py-2 font-semibold text-slate-950 hover:bg-amber-400">
                  Open review
                </button>
              )}
            </div>
          )}
        </aside>
      </div>

      {/* Bulletin drawer */}
      <section className="shrink-0 border-t border-white/10 bg-[#0C1424]">
        <div className="flex h-11 items-center justify-between px-4">
          <button onClick={() => setDrawerOpen((v) => !v)} aria-expanded={drawerOpen} className="flex items-center gap-3 text-sm hover:text-white">
            <span className="font-semibold text-white">Intelligence summary</span>
            {report && (
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${report.threat_tier === 'SEVERE' || report.threat_tier === 'HIGH' ? 'bg-rose-950 text-rose-300' : 'bg-emerald-950 text-emerald-300'}`}>
                {report.threat_tier}
              </span>
            )}
            {drawerOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </button>
          <ExportButton />
        </div>
        {drawerOpen && (
          <div className="grid max-h-56 gap-6 overflow-y-auto border-t border-white/5 p-4 text-sm md:grid-cols-3">
            {report && traceDone ? (
              <>
                <div>
                  <h3 className="mb-1 font-semibold text-amber-300">Summary</h3>
                  <p className="leading-relaxed text-slate-300">{report.executive_summary}</p>
                  <p className="mt-2 text-xs text-slate-500">The exported report adds imagery, features, counterfactuals, legal text, the full trace and an audit trail.</p>
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-cyan-300">Legal citations</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {report.statutory_violations.map((s, i) => <span key={i} className="rounded bg-cyan-950/60 px-2 py-1 text-xs text-cyan-200">{s}</span>)}
                  </div>
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-emerald-300">Recommended actions</h3>
                  <ul className="list-inside list-disc space-y-1 text-slate-300">{report.actionable_recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
                </div>
              </>
            ) : (
              <p className="text-slate-500 md:col-span-3">The summary appears here once the investigation finishes. Then use <strong className="text-slate-300">Export report</strong> to download the full PDF dossier.</p>
            )}
          </div>
        )}
      </section>

      {/* HITL modal */}
      {showHITL && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="hitl-title">
          <div className="glass-panel-elevated w-full max-w-lg rounded-2xl p-6">
            <div className="flex items-start justify-between gap-4">
              <h2 id="hitl-title" className="font-display text-xl font-semibold text-white">Analyst review required</h2>
              <button onClick={() => setShowHITL(false)} aria-label="Defer review" className="text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            <p className="mt-2 text-sm text-slate-300">The workflow paused at the human checkpoint. Record your decision; it is written to the audit ledger and included in the exported report.</p>
            <fieldset className="mt-5 space-y-2">
              <legend className="sr-only">Disposition</legend>
              {([['APPROVED', 'Confirm and escalate'], ['ESCALATED', 'Escalate for supervisor review'], ['REJECTED', 'Reject as false positive']] as [Disposition, string][]).map(([v, label]) => (
                <label key={v} className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 bg-slate-900/60 p-3 text-sm text-slate-100">
                  <input type="radio" name="disp" checked={disposition === v} onChange={() => setDisposition(v)} className="accent-amber-400" />
                  {label}
                </label>
              ))}
            </fieldset>
            <label className="mt-4 block text-sm text-slate-300">
              Audit notes <span className="text-slate-500">(min. 10 characters)</span>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className="mt-1 w-full rounded-lg border border-slate-700 bg-[#070B14] p-3 text-sm text-slate-100 outline-none focus:border-cyan-400" />
            </label>
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setShowHITL(false)} className="rounded-lg px-4 py-2 text-sm text-slate-300 hover:bg-white/10">Decide later</button>
              <button onClick={submitHITL} disabled={submitting || notes.trim().length < 10} className="rounded-lg bg-amber-500 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-40">
                {submitting ? 'Saving…' : 'Record decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
