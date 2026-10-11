import { useState } from 'react';
import { RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { ProvenanceChip } from '../components/ProvenanceChip';
import type { SanctionsScreenResult } from '../lib/api';
import { screenVessel } from '../lib/api';

const EXAMPLES = [{ label: 'IMO 9187629', imo: '9187629' }];

export const Screening = () => {
  const [name, setName] = useState('');
  const [imo, setImo] = useState('');
  const [mmsi, setMmsi] = useState('');
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [out, setOut] = useState<SanctionsScreenResult | null>(null);
  const [ms, setMs] = useState<number | null>(null);

  const canSearch = !!(name.trim() || imo.trim() || mmsi.trim());

  const search = async (override?: { imo?: string }) => {
    setBusy(true);
    setError(null);
    const t0 = performance.now();
    try {
      const res = await screenVessel({
        vessel_name: name.trim() || undefined,
        imo: (override?.imo ?? imo.trim()) || undefined,
        mmsi: mmsi.trim() || undefined,
        force_offline: offline,
      });
      setMs(performance.now() - t0);
      setOut(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Screening failed');
    } finally {
      setBusy(false);
    }
  };

  const r = out?.result;

  return (
    <div>
      <PageHeader
        eyebrow="Tool"
        title="Vessel screening"
        lead="Check a vessel against the official U.S. OFAC SDN list and the UN Security Council consolidated list, by IMO, MMSI or (fuzzy) name."
      />
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <form onSubmit={(e) => { e.preventDefault(); if (canSearch) search(); }} className="grid gap-4 rounded-2xl border border-white/10 bg-[#0C1424] p-6 sm:grid-cols-3">
          {[
            ['Vessel name', name, setName, 'e.g. ADRIAN DARYA'],
            ['IMO number', imo, setImo, '7 digits'],
            ['MMSI', mmsi, setMmsi, '9 digits'],
          ].map(([label, value, setter, ph]) => (
            <label key={label as string} className="text-sm text-slate-300">
              {label as string}
              <input value={value as string} onChange={(e) => (setter as (v: string) => void)(e.target.value)} placeholder={ph as string} className="mt-1 w-full rounded-lg border border-white/10 bg-[#070B14] px-3 py-2 text-slate-100 outline-none focus:border-cyan-400" />
            </label>
          ))}
          <div className="flex flex-wrap items-center gap-4 sm:col-span-3">
            <button type="submit" disabled={!canSearch || busy} className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50">
              {busy && <RefreshCw className="h-4 w-4 animate-spin" />} Screen vessel
            </button>
            <label className="flex items-center gap-2 text-sm text-slate-400"><input type="checkbox" checked={offline} onChange={(e) => setOffline(e.target.checked)} className="accent-amber-400" /> Simulate registry offline</label>
            <span className="ml-auto text-xs text-slate-500">
              Try:{' '}
              {EXAMPLES.map((ex) => (
                <button type="button" key={ex.label} onClick={() => { setImo(ex.imo); search({ imo: ex.imo }); }} className="text-cyan-400 underline underline-offset-2">{ex.label}</button>
              ))}
            </span>
          </div>
        </form>

        {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}

        {r && (
          <section className="mt-6" aria-live="polite">
            <div className={`flex items-start gap-4 rounded-2xl border p-6 ${r.is_sanctioned ? 'border-rose-500/40 bg-rose-950/20' : 'border-emerald-500/30 bg-emerald-950/10'}`}>
              {r.is_sanctioned ? <ShieldAlert className="h-7 w-7 text-rose-400" /> : <ShieldCheck className="h-7 w-7 text-emerald-400" />}
              <div>
                <h2 className="font-display text-xl font-semibold text-white">{r.is_sanctioned ? 'Registry match found' : 'No registry match'}</h2>
                <p className="mt-1 text-sm text-slate-300">Risk: <strong>{r.overall_sanctions_risk}</strong> · Query: {r.query_target} · Sources: {r.screened_sources.join(', ')}{ms != null && ` · ${ms.toFixed(0)} ms`}</p>
                {r.screening_notes && <p className="mt-1 text-sm text-slate-400">{r.screening_notes}</p>}
                {out?.is_degraded && <p className="mt-2 text-sm text-amber-300">Degraded mode: the live registry was unavailable, so this is an unverified baseline.</p>}
              </div>
            </div>

            {r.matches.length > 0 && (
              <div className="mt-4 overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="bg-[#0C1424] text-xs uppercase text-slate-400"><tr><th className="p-3">List</th><th className="p-3">Entity</th><th className="p-3">IMO / MMSI</th><th className="p-3">Programmes</th><th className="p-3">Score</th><th className="p-3">Basis</th></tr></thead>
                  <tbody className="divide-y divide-white/5">
                    {r.matches.map((m, i) => (
                      <tr key={i}>
                        <td className="p-3 text-slate-300">{m.source_list}</td>
                        <td className="p-3 font-medium text-white">{m.entity_name}{m.flag_state && <div className="text-xs font-normal text-slate-500">Flag: {m.flag_state}</div>}</td>
                        <td className="p-3 font-mono text-xs text-slate-300">{m.matched_imo ?? '—'} / {m.matched_mmsi ?? '—'}</td>
                        <td className="p-3 text-slate-300">{m.sanction_programs.join(', ') || '—'}</td>
                        <td className="p-3">{m.match_score.toFixed(2)}</td>
                        <td className="p-3 text-xs text-slate-400">{m.match_basis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-4 flex items-center gap-2 text-xs text-slate-500"><ProvenanceChip provenance="REAL" /> Official lists parsed from the XML files in data/raw/sanctions. A fuzzy name match is a lead, not proof of identity.</p>
          </section>
        )}
      </div>
    </div>
  );
};
