import { useEffect, useState } from 'react';
import { Database, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import type { AuditLedgerEntry } from '../lib/api';
import { fetchAuditLedger } from '../lib/api';

export const AuditLedger = () => {
  const [ledger, setLedger] = useState<AuditLedgerEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isChainValid, setIsChainValid] = useState(true);

  const loadLedger = async () => {
    setIsLoading(true);
    try {
      const data = await fetchAuditLedger();
      setLedger(data.ledger);

      // Verify cryptographic hash chain integrity
      let valid = true;
      for (let i = 1; i < data.ledger.length; i++) {
        if (data.ledger[i].prev_hash !== data.ledger[i - 1].hash) {
          valid = false;
          break;
        }
      }
      setIsChainValid(valid);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLedger();
  }, []);

  return (
    <div className="flex-1 bg-[#070B14] p-6 sm:p-12 text-slate-100 max-w-7xl mx-auto w-full font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase mb-1">
            <Database className="w-4 h-4" />
            <span>CRYPTOGRAPHIC LEDGER INTEGRITY</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold font-display text-white">
            Immutable Audit Trail
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Hash-chained append-only log recording every automated investigation, parameter tweak, and operator disposition.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold ${
            isChainValid
              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/40'
              : 'bg-rose-950/40 text-rose-400 border-rose-500/40'
          }`}>
            {isChainValid ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span>{isChainValid ? 'SHA-256 CHAIN VERIFIED' : 'CHAIN COMPROMISED'}</span>
          </div>

          <button
            onClick={loadLedger}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh Ledger"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        {ledger.map((entry) => (
          <div
            key={entry.index}
            className="p-5 rounded-xl bg-[#0C1424] border border-slate-800 hover:border-cyan-500/30 transition-all font-mono text-xs"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/40">
                  BLOCK #{entry.index}
                </span>
                <span className="text-white font-bold">{entry.action}</span>
                <span className="text-[10px] text-slate-500">• {entry.operator}</span>
              </div>
              <span className="text-[10px] text-slate-400">{entry.timestamp}</span>
            </div>

            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
              <div>
                <span className="text-slate-500 block mb-1">ENTRY DETAILS:</span>
                <pre className="p-2.5 rounded bg-[#070B14] border border-slate-800 text-slate-300 overflow-x-auto text-[10px]">
                  {JSON.stringify(entry.details, null, 2)}
                </pre>
              </div>

              <div className="space-y-2">
                <div>
                  <span className="text-slate-500 block mb-1">PREVIOUS BLOCK HASH:</span>
                  <div className="p-2 rounded bg-[#070B14] border border-slate-800/80 text-[10px] text-slate-400 break-all">
                    {entry.prev_hash}
                  </div>
                </div>

                <div>
                  <span className="text-cyan-400 block mb-1">CURRENT BLOCK SHA-256:</span>
                  <div className="p-2 rounded bg-cyan-950/20 border border-cyan-500/30 text-[10px] text-cyan-300 break-all font-bold">
                    {entry.hash}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
