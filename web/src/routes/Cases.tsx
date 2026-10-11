import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, RefreshCw, ArrowRight } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { ProvenanceChip } from '../components/ProvenanceChip';
import type { SavedCase } from '../lib/api';
import { fetchSavedCases, downloadReportPdf } from '../lib/api';

const tierCls: Record<string, string> = {
  SEVERE: 'bg-rose-950 text-rose-300',
  HIGH: 'bg-orange-950 text-orange-300',
  MEDIUM: 'bg-amber-950 text-amber-300',
  LOW: 'bg-emerald-950 text-emerald-300',
};

export const Cases = () => {
  const [cases, setCases] = useState<SavedCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<string>('ALL');
  const [kind, setKind] = useState<'ALL' | 'REAL' | 'SYNTHETIC'>('ALL');
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    fetchSavedCases().then((r) => setCases(r.cases)).catch((e) => setError(e.message));
  }, []);

  const shown = useMemo(
    () =>
      (cases ?? []).filter(
        (c) => (tier === 'ALL' || c.threat_tier === tier) && (kind === 'ALL' || (kind === 'REAL') === c.is_real),
      ),
    [cases, tier, kind],
  );

  const download = async (c: SavedCase) => {
    if (!c.report_id) return;
    setBusy(c.mission_id);
    try {
      await downloadReportPdf(c.report_id, false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Case library"
        title="Past investigations"
        lead="Every investigation you run is saved. Re-download its full PDF dossier, or run the same case again in the Operations console."
        actions={
          <Link to="/ops" className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300">
            New investigation <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-5 flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2 text-slate-400">
            Threat tier
            <select value={tier} onChange={(e) => setTier(e.target.value)} className="rounded-md border border-white/10 bg-[#0C1424] px-2 py-1.5 text-slate-100">
              {['ALL', 'SEVERE', 'HIGH', 'MEDIUM', 'LOW'].map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-slate-400">
            Data
            <select value={kind} onChange={(e) => setKind(e.target.value as typeof kind)} className="rounded-md border border-white/10 bg-[#0C1424] px-2 py-1.5 text-slate-100">
              <option value="ALL">All</option>
              <option value="REAL">Real chips</option>
              <option value="SYNTHETIC">Synthetic scenarios</option>
            </select>
          </label>
          <span className="ml-auto text-slate-500">{shown.length} of {cases?.length ?? 0}</span>
        </div>

        {error && <p className="mb-4 text-sm text-rose-400">{error}</p>}
        {!cases && !error && <p className="flex items-center gap-2 text-slate-400"><RefreshCw className="h-4 w-4 animate-spin" /> Loading…</p>}
        {cases && cases.length === 0 && (
          <div className="rounded-2xl border border-dashed border-white/15 p-10 text-center text-slate-400">
            No investigations yet. <Link to="/ops" className="text-cyan-400 underline">Run one in Operations</Link> and it will appear here.
          </div>
        )}

        {shown.length > 0 && (
          <div className="overflow-x-auto rounded-2xl border border-white/10">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-[#0C1424] text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="p-3">When (UTC)</th>
                  <th className="p-3">Case</th>
                  <th className="p-3">Tier</th>
                  <th className="p-3">Classification</th>
                  <th className="p-3">p(dark)</th>
                  <th className="p-3">Notes</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {shown.map((c) => (
                  <tr key={c.mission_id} className="hover:bg-white/[0.03]">
                    <td className="p-3 whitespace-nowrap text-slate-300">{(c.created_at ?? '').slice(0, 16).replace('T', ' ')}</td>
                    <td className="p-3">
                      <div className="max-w-[220px] truncate font-mono text-xs text-cyan-300" title={c.case}>{c.case}</div>
                      <div className="mt-1 flex gap-1.5">
                        <ProvenanceChip provenance={c.is_real ? 'REAL' : 'SYNTHETIC'} />
                        {c.ais_withheld && <span className="rounded bg-amber-950 px-1.5 py-0.5 text-[11px] text-amber-300">AIS cut</span>}
                      </div>
                    </td>
                    <td className="p-3"><span className={`rounded px-2 py-0.5 text-xs font-semibold ${tierCls[c.threat_tier ?? ''] ?? 'bg-slate-800 text-slate-300'}`}>{c.threat_tier ?? '—'}</span></td>
                    <td className="p-3 text-slate-300">{c.classification ?? '—'}</td>
                    <td className="p-3 font-stat text-slate-100">{c.probability != null ? c.probability.toFixed(2) : '—'}</td>
                    <td className="p-3 text-xs text-slate-400">
                      {c.hitl_required ? (c.hitl_decisions ? 'Reviewed' : 'Awaiting review') : 'No review needed'}
                      {!c.in_coverage && <div>Outside dataset coverage</div>}
                      {c.degradations > 0 && <div>{c.degradations} degradation(s)</div>}
                    </td>
                    <td className="p-3">
                      <div className="flex justify-end gap-2">
                        <Link to={`/ops/case/${encodeURIComponent(c.case)}`} className="rounded-md border border-white/10 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-white/10">Re-run</Link>
                        <button
                          onClick={() => download(c)}
                          disabled={!c.report_id || busy === c.mission_id}
                          className="inline-flex items-center gap-1.5 rounded-md bg-cyan-400 px-2.5 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                        >
                          {busy === c.mission_id ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />} PDF
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
