import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, RefreshCw, Upload } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { ProvenanceChip } from '../components/ProvenanceChip';
import type { RealCaseRow, ScenarioFixture, SARDetection } from '../lib/api';
import { fetchRealCases, fetchRealCase } from '../lib/api';

type Band = 'vv' | 'vh' | 'rgb';

export const SarLab = () => {
  const [rows, setRows] = useState<RealCaseRow[]>([]);
  const [query, setQuery] = useState('');
  const [chipId, setChipId] = useState<string | null>(null);
  const [band, setBand] = useState<Band>('vv');
  const [conf, setConf] = useState(0.35);
  const [boxes, setBoxes] = useState(true);
  const [data, setData] = useState<ScenarioFixture | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [upload, setUpload] = useState<{ name: string; dets: SARDetection[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchRealCases().then((r) => { setRows(r.cases); if (r.cases[0]) setChipId(r.cases[0].chip_id); }).catch((e) => setError(e.message));
  }, []);

  // Debounce the slider so the detector is not re-run on every pixel of drag.
  useEffect(() => {
    if (!chipId) return;
    let live = true;
    const t = setTimeout(() => {
      setLoading(true);
      setError(null);
      fetchRealCase(chipId, conf)
        .then((d) => live && setData(d))
        .catch((e) => live && (setData(null), setError(e.message)))
        .finally(() => live && setLoading(false));
    }, 350);
    return () => { live = false; clearTimeout(t); };
  }, [chipId, conf]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => !q || r.vessel_name.toLowerCase().includes(q) || r.mmsi.includes(q) || r.vessel_type.toLowerCase().includes(q));
  }, [rows, query]);

  const onUpload = async (file: File) => {
    setError(null);
    const fd = new FormData();
    fd.append('chip_file', file);
    fd.append('confidence_threshold', String(conf));
    const res = await fetch('/api/detect/sar', { method: 'POST', body: fd });
    const body = await res.json();
    if (!res.ok) { setError(body.detail ?? 'Upload failed'); return; }
    setUpload({ name: file.name, dets: body.all_detections ?? [] });
  };

  const primary = data?.sar_detection;
  const truth = data?.ground_truth;
  const imgSrc = chipId ? `/api/chips/${encodeURIComponent(chipId)}/image?band=${band}&boxes=${boxes}&conf=${conf}` : '';

  return (
    <div>
      <PageHeader
        eyebrow="Tool"
        title="SAR Lab"
        lead="Inspect real Sentinel-1 radar chips, run the vessel detector, and compare what it measures with the vessel’s own AIS."
      />
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[300px_1fr]">
        <aside className="min-w-0">
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name, MMSI, type…" aria-label="Search chips" className="w-full rounded-lg border border-white/10 bg-[#0C1424] py-2 pl-8 pr-3 text-sm outline-none focus:border-cyan-400" />
          </div>
          <div className="max-h-[560px] space-y-1.5 overflow-y-auto pr-1">
            {filtered.map((r) => (
              <button key={r.chip_id} onClick={() => { setChipId(r.chip_id); setUpload(null); }} aria-pressed={r.chip_id === chipId}
                className={`w-full rounded-lg border p-2.5 text-left text-sm transition ${r.chip_id === chipId ? 'border-cyan-500/60 bg-cyan-950/30' : 'border-white/10 bg-[#0C1424] hover:border-white/20'}`}>
                <div className="flex justify-between gap-2"><span className="truncate font-medium text-white">{r.vessel_name || 'Unnamed'}</span><span className="text-xs text-slate-500">{r.true_length_m.toFixed(0)} m</span></div>
                <div className="text-xs text-slate-400">{r.vessel_type} · {r.acq_time.slice(0, 10)}</div>
              </button>
            ))}
            {!filtered.length && <p className="text-sm text-slate-500">No chips match.</p>}
          </div>
          <div className="mt-4 rounded-xl border border-dashed border-white/15 p-4 text-sm text-slate-400">
            <p className="font-medium text-slate-200">Upload your own chip</p>
            <p className="mt-1 text-xs">A <code>.npz</code> with <code>chip_vv</code> and <code>chip_vh</code> arrays (≤ 2048², ≤ 25 MB).</p>
            <input ref={fileRef} type="file" accept=".npz" hidden onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} />
            <button onClick={() => fileRef.current?.click()} className="mt-3 inline-flex items-center gap-2 rounded-md border border-white/15 px-3 py-1.5 text-xs text-slate-200 hover:bg-white/10"><Upload className="h-3.5 w-3.5" /> Choose file</button>
          </div>
        </aside>

        <section className="min-w-0">
          {error && <p className="mb-3 rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-sm text-rose-300">{error}</p>}
          {upload ? (
            <div className="rounded-2xl border border-white/10 bg-[#0C1424] p-6">
              <h2 className="font-display text-xl font-semibold text-white">Uploaded: {upload.name}</h2>
              <p className="mt-1 text-sm text-slate-400">{upload.dets.length} detection(s) at confidence ≥ {conf.toFixed(2)}. Positions are not georeferenced for uploads.</p>
              <DetectionTable dets={upload.dets} primaryId={null} />
            </div>
          ) : (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-4 rounded-xl border border-white/10 bg-[#0C1424] p-3 text-sm">
                <div className="flex gap-1 rounded-lg bg-[#070B14] p-1" role="tablist">
                  {(['vv', 'vh', 'rgb'] as Band[]).map((b) => (
                    <button key={b} role="tab" aria-selected={band === b} onClick={() => setBand(b)} className={`rounded-md px-3 py-1.5 text-xs uppercase ${band === b ? 'bg-cyan-500/20 text-cyan-200' : 'text-slate-400 hover:text-white'}`}>{b === 'rgb' ? 'Composite' : b}</button>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-slate-300">Confidence ≥ {conf.toFixed(2)}
                  <input type="range" min={0.1} max={0.9} step={0.05} value={conf} onChange={(e) => setConf(Number(e.target.value))} className="accent-cyan-400" />
                </label>
                <label className="flex items-center gap-2 text-slate-300"><input type="checkbox" checked={boxes} onChange={(e) => setBoxes(e.target.checked)} className="accent-cyan-400" /> Show boxes</label>
                {loading && <span className="flex items-center gap-2 text-xs text-slate-400"><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Detecting…</span>}
              </div>

              <div className="grid gap-6 xl:grid-cols-[minmax(0,520px)_1fr]">
                <div>
                  {imgSrc && <img src={imgSrc} alt={`Real Sentinel-1 ${band} chip`} className="w-full rounded-xl border border-cyan-500/30 [image-rendering:pixelated]" />}
                  <p className="mt-2 flex items-center gap-2 text-xs text-slate-400"><ProvenanceChip provenance="REAL" /> Sentinel-1 IW GRDH · cyan = target, amber = others, dashed = clutter guard</p>
                </div>
                <div className="space-y-4">
                  {data && primary && (
                    <div className="rounded-2xl border border-white/10 bg-[#0C1424] p-5">
                      <h2 className="font-display text-lg font-semibold text-white">{data.ground_truth?.vessel_name ?? 'Target'}</h2>
                      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        {[
                          ['Measured length', `${primary.length_m.toFixed(0)} m`],
                          ['True length (own AIS)', truth ? `${truth.length_m.toFixed(0)} m` : '—'],
                          ['Length error', truth ? `${(primary.length_m - truth.length_m >= 0 ? '+' : '') + (primary.length_m - truth.length_m).toFixed(0)} m` : '—'],
                          ['Confidence', `${(primary.confidence * 100).toFixed(0)}%`],
                          ['Target/clutter', `${(primary.target_clutter_ratio_db ?? 0).toFixed(1)} dB`],
                          ['Acquired', primary.timestamp.slice(0, 16).replace('T', ' ') + ' UTC'],
                        ].map(([k, v]) => (<div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="font-medium text-white">{v}</dd></div>))}
                      </dl>
                      <p className="mt-3 text-xs text-slate-500">Length comes from an axis-aligned box at 10 m pixels, so ±10 m is expected.</p>
                    </div>
                  )}
                  {data && <DetectionTable dets={data.all_detections ?? []} primaryId={primary?.detection_id ?? null} />}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};

const DetectionTable = ({ dets, primaryId }: { dets: SARDetection[]; primaryId: string | null }) => (
  <div className="mt-4 overflow-x-auto rounded-xl border border-white/10">
    <table className="w-full min-w-[480px] text-left text-sm">
      <thead className="bg-[#0C1424] text-xs uppercase text-slate-400"><tr><th className="p-2.5">Detection</th><th className="p-2.5">Conf.</th><th className="p-2.5">L (m)</th><th className="p-2.5">B (m)</th><th className="p-2.5">TCR dB</th></tr></thead>
      <tbody className="divide-y divide-white/5">
        {dets.map((d) => (
          <tr key={d.detection_id} className={d.detection_id === primaryId ? 'bg-cyan-950/20' : ''}>
            <td className="p-2.5 font-mono text-xs text-slate-300">{d.detection_id.slice(-18)}{d.detection_id === primaryId && ' · target'}</td>
            <td className="p-2.5">{d.confidence.toFixed(2)}</td><td className="p-2.5">{d.length_m.toFixed(0)}</td><td className="p-2.5">{d.width_m.toFixed(0)}</td><td className="p-2.5">{(d.target_clutter_ratio_db ?? 0).toFixed(1)}</td>
          </tr>
        ))}
        {!dets.length && <tr><td colSpan={5} className="p-4 text-slate-500">No detections at this threshold.</td></tr>}
      </tbody>
    </table>
  </div>
);
