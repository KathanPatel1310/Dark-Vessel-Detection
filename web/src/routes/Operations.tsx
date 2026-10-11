import { useState, useEffect, useRef } from 'react';
import { Play, ShieldAlert, Download, ChevronUp, ChevronDown, RefreshCw, Check, X } from 'lucide-react';
import { ProvenanceChip } from '../components/ProvenanceChip';
import { TacticalMap } from '../components/TacticalMap';
import type { ScenarioFixture, InvestigationResult } from '../lib/api';
import { fetchScenarios, runInvestigation, submitHITLDecision } from '../lib/api';

interface OperationsProps {
  initialScenarioId?: string;
}

type Tab = 'map' | 'sar' | 'fusion';
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
  const [selectedId, setSelectedId] = useState(initialScenarioId);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [cutAIS, setCutAIS] = useState(false);
  const [offlineSanctions, setOfflineSanctions] = useState(false);

  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [revealed, setRevealed] = useState(0);
  const [tab, setTab] = useState<Tab>('map');
  const [drawerOpen, setDrawerOpen] = useState(true);

  const [showHITL, setShowHITL] = useState(false);
  const [hitlDone, setHitlDone] = useState(false);
  const [disposition, setDisposition] = useState<Disposition>('APPROVED');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const chipRef = useRef<HTMLCanvasElement | null>(null);
  const selected = scenarios.find((s) => s.scenario_id === selectedId) ?? null;

  useEffect(() => {
    fetchScenarios()
      .then((list) => {
        setScenarios(list);
        if (!list.some((s) => s.scenario_id === initialScenarioId) && list[0]) setSelectedId(list[0].scenario_id);
      })
      .catch((e) => setLoadError(e.message));
  }, [initialScenarioId]);

  useEffect(() => setSelectedId(initialScenarioId), [initialScenarioId]);

  const reset = () => {
    setResult(null);
    setRevealed(0);
    setShowHITL(false);
    setHitlDone(false);
    setRunError(null);
  };

  const selectScenario = (id: string) => {
    setSelectedId(id);
    reset();
  };

  // Reveal trace steps one at a time so the 7-node workflow reads as it executes
  useEffect(() => {
    if (!result) return;
    const total = result.execution_trace.length;
    if (revealed >= total) {
      if (result.human_in_the_loop_required && !hitlDone) setShowHITL(true);
      return;
    }
    const t = setTimeout(() => setRevealed((n) => n + 1), 280);
    return () => clearTimeout(t);
  }, [result, revealed, hitlDone]);

  // Esc defers the HITL dialog
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
    try {
      const res = await runInvestigation({
        mission_id: `OPS-${selected.scenario_id}-${Date.now().toString().slice(-4)}`,
        sar_detection: selected.sar_detection,
        matched_ais: cutAIS ? null : selected.ais_observation,
        historical_gaps: selected.historical_gaps ?? [],
        simulate_ais_offline: cutAIS || selected.scenario_type === 'DEGRADED_EVIDENCE',
        simulate_sanctions_offline: offlineSanctions || selected.scenario_type === 'DEGRADED_EVIDENCE',
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

  // SAR viewer — schematic from detection metadata (deterministic speckle, not random per render)
  useEffect(() => {
    const canvas = chipRef.current;
    if (!canvas || !selected || tab !== 'sar') return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const det = selected.sar_detection;
    const w = canvas.width;
    const h = canvas.height;
    let seed = 1234;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const img = ctx.createImageData(w, h);
    for (let i = 0; i < img.data.length; i += 4) {
      const n = rnd() * 26;
      img.data[i] = n;
      img.data[i + 1] = n + 4;
      img.data[i + 2] = n + 10;
      img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);

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
    ctx.lineWidth = 1.5;
    ctx.strokeRect(-len / 2, -beam / 2, len, beam);
    ctx.restore();

    ctx.font = '12px "JetBrains Mono Variable", monospace';
    ctx.fillStyle = '#00E5FF';
    ctx.fillText(`L ${det.length_m.toFixed(0)} m  ·  B ${det.width_m.toFixed(0)} m  ·  conf ${(det.confidence * 100).toFixed(0)}%`, 14, 24);
    ctx.fillStyle = '#F59E0B';
    ctx.fillText('amber dashed = clutter guard window', 14, h - 14);
  }, [selected, tab]);

  const steps = result?.execution_trace.slice(0, revealed) ?? [];
  const traceDone = !!result && revealed >= result.execution_trace.length;
  const report = result?.final_report ?? null;
  const detection = selected?.sar_detection;
  const aisUsed = cutAIS ? null : selected?.ais_observation ?? null;
  const spatialKm =
    detection && aisUsed
      ? haversineKm([detection.latitude, detection.longitude], [aisUsed.latitude, aisUsed.longitude])
      : null;

  const stepState = (n: 1 | 2 | 3) =>
    n === 1 ? (selected ? 'done' : 'active') : n === 2 ? (result ? 'done' : selected ? 'active' : 'idle') : traceDone ? 'active' : 'idle';

  return (
    <div className="flex h-[calc(100dvh-4rem)] flex-col overflow-hidden bg-[#070B14]">
      {/* Sub-bar */}
      <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 bg-[#0C1424] px-4 py-2 text-sm">
        <div className="flex min-w-0 items-center gap-3">
          <span className="font-mono text-cyan-400">{selectedId}</span>
          <span className="hidden truncate text-slate-300 sm:inline">{selected?.scenario_name}</span>
          <ProvenanceChip provenance={selected?.provenance?.radar ?? 'SYNTHETIC'} />
        </div>
        <button
          onClick={() => window.open(`/api/report/${report?.report_id ?? ''}/export?format=html`, '_blank')}
          disabled={!report}
          className="flex items-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-slate-200 transition hover:bg-white/10 disabled:opacity-40"
        >
          <Download className="h-4 w-4 text-cyan-400" /> Export bulletin
        </button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[320px_1fr_360px]">
        {/* LEFT */}
        <aside className="flex min-h-0 flex-col gap-5 overflow-y-auto border-b border-white/10 p-4 lg:border-b-0 lg:border-r">
          <ol className="flex items-center gap-2 text-xs">
            {['Select', 'Run', 'Review'].map((label, i) => {
              const s = stepState((i + 1) as 1 | 2 | 3);
              return (
                <li key={label} className="flex flex-1 items-center gap-2">
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold ${
                      s === 'done'
                        ? 'border-cyan-400 bg-cyan-400 text-slate-950'
                        : s === 'active'
                          ? 'border-cyan-400 text-cyan-300'
                          : 'border-slate-700 text-slate-600'
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
            <h2 className="mb-2 text-sm font-semibold text-white">1. Choose a scenario</h2>
            {loadError && <p className="text-sm text-rose-400">Could not load scenarios: {loadError}. Is the API running?</p>}
            <div className="space-y-2">
              {scenarios.map((s) => (
                <button
                  key={s.scenario_id}
                  onClick={() => selectScenario(s.scenario_id)}
                  aria-pressed={s.scenario_id === selectedId}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    s.scenario_id === selectedId
                      ? 'border-cyan-500/60 bg-cyan-950/30'
                      : 'border-white/10 bg-[#0C1424] hover:border-white/20'
                  }`}
                >
                  <div className="text-sm font-medium text-white">{s.scenario_name}</div>
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{s.description}</p>
                </button>
              ))}
            </div>
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
          </section>

          <section>
            <h2 className="mb-2 text-sm font-semibold text-white">2. Run the investigation</h2>
            <button
              onClick={run}
              disabled={isRunning || !selected}
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
              <button
                key={k}
                role="tab"
                aria-selected={tab === k}
                onClick={() => setTab(k)}
                className={`rounded-md px-3 py-1.5 transition ${tab === k ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:text-white'}`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="relative min-h-0 flex-1">
            {tab === 'map' && (
              <TacticalMap detection={detection} ais={aisUsed} waypoints={result?.forecast?.extrapolated_waypoints} />
            )}
            {tab === 'sar' && (
              <div className="flex h-full flex-col items-center justify-center gap-3 p-6">
                <canvas ref={chipRef} width={480} height={340} className="max-w-full rounded-xl border border-cyan-500/30" />
                <p className="max-w-md text-center text-xs text-slate-500">
                  Schematic rendering from detection metadata (size, aspect ratio, heading) — not the raw radar chip.
                </p>
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
                    ['Detector confidence', `${(detection.confidence * 100).toFixed(0)}%`],
                    [
                      'Dark-vessel hypothesis',
                      result ? `${(result.risk_assessment.dark_vessel_probability * 100).toFixed(0)}% — ${result.risk_assessment.dark_vessel_classification}` : 'Run an investigation',
                    ],
                    ['Distance to coast', result?.geo_context ? `${result.geo_context.distance_to_coast_km.toFixed(0)} km` : '—'],
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
              Choose a scenario and press <strong className="text-slate-200">Run investigation</strong>. Each of the agent nodes will appear here as it executes.
            </p>
          )}
          {isRunning && <p className="text-sm text-slate-400">Executing LangGraph workflow…</p>}

          <ol className="space-y-2">
            {steps.map((s) => (
              <li key={s.step_number} className="rounded-lg border border-white/10 bg-[#0C1424] p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-white">
                    {s.step_number}. {s.agent_name}
                  </span>
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
        <button onClick={() => setDrawerOpen((v) => !v)} aria-expanded={drawerOpen} className="flex h-10 w-full items-center justify-between px-4 text-sm hover:bg-white/5">
          <span className="flex items-center gap-3">
            <span className="font-semibold text-white">Intelligence bulletin</span>
            {report && (
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${report.threat_tier === 'SEVERE' || report.threat_tier === 'HIGH' ? 'bg-rose-950 text-rose-300' : 'bg-emerald-950 text-emerald-300'}`}>
                {report.threat_tier}
              </span>
            )}
          </span>
          {drawerOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </button>
        {drawerOpen && (
          <div className="grid max-h-56 gap-6 overflow-y-auto border-t border-white/5 p-4 text-sm md:grid-cols-3">
            {report && traceDone ? (
              <>
                <div>
                  <h3 className="mb-1 font-semibold text-amber-300">Summary</h3>
                  <p className="leading-relaxed text-slate-300">{report.executive_summary}</p>
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-cyan-300">Legal citations</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {report.statutory_violations.map((s, i) => (
                      <span key={i} className="rounded bg-cyan-950/60 px-2 py-1 text-xs text-cyan-200">{s}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-emerald-300">Recommended actions</h3>
                  <ul className="list-inside list-disc space-y-1 text-slate-300">
                    {report.actionable_recommendations.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              </>
            ) : (
              <p className="text-slate-500 md:col-span-3">The bulletin appears here once the investigation finishes.</p>
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
              <button onClick={() => setShowHITL(false)} aria-label="Defer review" className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="mt-2 text-sm text-slate-300">
              The workflow paused at the human checkpoint. Record your decision; it is written to the audit ledger.
            </p>
            <fieldset className="mt-5 space-y-2">
              <legend className="sr-only">Disposition</legend>
              {([
                ['APPROVED', 'Confirm and escalate'],
                ['ESCALATED', 'Escalate for supervisor review'],
                ['REJECTED', 'Reject as false positive'],
              ] as [Disposition, string][]).map(([v, label]) => (
                <label key={v} className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 bg-slate-900/60 p-3 text-sm text-slate-100">
                  <input type="radio" name="disp" checked={disposition === v} onChange={() => setDisposition(v)} className="accent-amber-400" />
                  {label}
                </label>
              ))}
            </fieldset>
            <label className="mt-4 block text-sm text-slate-300">
              Audit notes <span className="text-slate-500">(min. 10 characters)</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-[#070B14] p-3 text-sm text-slate-100 outline-none focus:border-cyan-400"
              />
            </label>
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setShowHITL(false)} className="rounded-lg px-4 py-2 text-sm text-slate-300 hover:bg-white/10">Decide later</button>
              <button
                onClick={submitHITL}
                disabled={submitting || notes.trim().length < 10}
                className="rounded-lg bg-amber-500 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-40"
              >
                {submitting ? 'Saving…' : 'Record decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
