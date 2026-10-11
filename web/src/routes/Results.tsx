import { useEffect, useState } from 'react';
import { PageHeader, Card } from '../components/PageHeader';
import type { ResultsPayload } from '../lib/api';
import { fetchResults } from '../lib/api';

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export const Results = () => {
  const [res, setRes] = useState<ResultsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchResults().then(setRes).catch((e) => setError(e.message));
  }, []);

  const subsets = res?.real_ablation ? Object.entries(res.real_ablation.subsets) : [];
  const llmKeys = res?.llm_eval ? Object.entries(res.llm_eval).filter(([, v]) => typeof v === 'number') : [];

  return (
    <div>
      <PageHeader
        eyebrow="Reference"
        title="Measured results"
        lead="Numbers exactly as recorded in the project’s report files. The app displays them; it does not recompute them."
      />
      <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        {error && <p className="text-sm text-rose-400">{error}</p>}
        {!res && !error && <p className="text-slate-400">Loading…</p>}

        {res?.real_ablation && (
          <Card>
            <h2 className="font-display text-xl font-semibold text-white">Feature ablation on real chips</h2>
            <p className="mt-1 text-sm text-slate-400">{res.real_ablation.task_description} · {res.real_ablation.total_real_chips_analyzed} real chips · recorded {res.real_ablation.timestamp}</p>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[600px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-400"><tr><th className="py-2 pr-3">Feature set</th><th className="px-3">Features</th><th className="px-3">ROC-AUC</th><th className="px-3">F1</th><th className="px-3">Accuracy</th><th className="pl-3">Brier</th></tr></thead>
                <tbody className="divide-y divide-white/5">
                  {subsets.map(([name, m]) => (
                    <tr key={name}>
                      <td className="py-2.5 pr-3 font-medium text-white">{name}</td>
                      <td className="px-3 text-slate-300">{m.feature_count}</td>
                      <td className="px-3"><div className="flex items-center gap-2"><div className="h-1.5 w-24 rounded bg-white/10"><div className="h-full rounded bg-cyan-400" style={{ width: pct(m.roc_auc) }} /></div><span className="font-stat text-slate-100">{m.roc_auc.toFixed(3)}</span></div></td>
                      <td className="px-3 text-slate-300">{m.f1_score.toFixed(3)}</td>
                      <td className="px-3 text-slate-300">{pct(m.accuracy)}</td>
                      <td className="pl-3 text-slate-300">{m.brier_score.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">
              The task here is identifying tankers from radar and AIS features. It is an offline experiment (a Random Forest), <em>not</em> the live risk score, which is rule-based. These figures have not been independently reproduced.
            </p>
          </Card>
        )}

        {res?.agent_scenarios && (
          <Card>
            <h2 className="font-display text-xl font-semibold text-white">Agent workflow audit (10 scenarios)</h2>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-400"><tr><th className="py-2 pr-3">Scenario</th><th className="px-3">Status</th><th className="px-3">Nodes</th><th className="px-3">Degradations</th><th className="px-3">Human review</th><th className="px-3">Tier</th><th className="pl-3">ms</th></tr></thead>
                <tbody className="divide-y divide-white/5">
                  {res.agent_scenarios.map((s) => (
                    <tr key={s.scenario_id}>
                      <td className="py-2.5 pr-3 text-white">{s.scenario_id}. {s.name}</td>
                      <td className={`px-3 font-semibold ${s.status === 'PASSED' ? 'text-emerald-400' : 'text-rose-400'}`}>{s.status}</td>
                      <td className="px-3 text-slate-300">{s.nodes_executed.length}</td>
                      <td className="px-3 text-slate-300">{s.degradation_events_count}</td>
                      <td className="px-3 text-slate-300">{s.hitl_interrupted ? 'Yes' : 'No'}</td>
                      <td className="px-3 text-slate-300">{s.final_threat_tier}</td>
                      <td className="pl-3 font-mono text-xs text-slate-400">{s.duration_ms.toFixed(0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {llmKeys.length > 0 && (
          <Card>
            <h2 className="font-display text-xl font-semibold text-white">Report-language model evaluation</h2>
            <dl className="mt-5 grid gap-4 sm:grid-cols-3">
              {llmKeys.map(([k, v]) => (
                <div key={k} className="rounded-xl bg-[#070B14] p-4">
                  <dt className="text-xs text-slate-500">{k.replace(/_/g, ' ')}</dt>
                  <dd className="mt-1 font-stat text-2xl text-white">{Number(v) <= 1 ? pct(Number(v)) : String(v)}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">
              These are format-and-grounding checks on a small held-out set of rule-generated examples (the training data is itself template-written), so a high score shows format fidelity, not analytical skill.
              {res?.llm_eval?.evaluation_target ? ` Target evaluated: ${String(res.llm_eval.evaluation_target)}.` : ''}
            </p>
          </Card>
        )}

        {res && res.sources.length > 0 && (
          <Card>
            <h2 className="font-display text-lg font-semibold text-white">Source files</h2>
            <ul className="mt-3 space-y-2 text-xs text-slate-400">
              {res.sources.map((s) => (
                <li key={s.key}><span className="font-mono text-slate-300">{s.file}</span> · modified {s.modified.slice(0, 10)}<div className="break-all font-mono text-[10px] text-slate-600">SHA-256 {s.sha256}</div></li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
};
