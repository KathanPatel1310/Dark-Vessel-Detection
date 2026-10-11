import { useEffect, useState } from 'react';

export type HealthState = 'checking' | 'online' | 'degraded' | 'offline';

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>('checking');
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const r = await fetch('/api/readyz');
        if (!r.ok) throw new Error();
        const j = await r.json();
        // The optional LLM adapter is expected to be on rule-based fallback; only core components count.
        const { llm: _llm, ...core } = (j.components ?? {}) as Record<string, { status: string }>;
        const degraded = Object.values(core).some((c) => c.status !== 'READY');
        if (alive) setState(degraded ? 'degraded' : 'online');
      } catch {
        if (alive) setState('offline');
      }
    };
    check();
    const id = setInterval(check, 30000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);
  return state;
}
