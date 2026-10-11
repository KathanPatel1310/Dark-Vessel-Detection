import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Showcase } from './routes/Showcase';
import { Operations } from './routes/Operations';
import { AuditLedger } from './routes/AuditLedger';
import { Methodology } from './routes/Methodology';
import { DevPlayground } from './routes/DevPlayground';

export function App() {
  const [currentRoute, setCurrentRoute] = useState<string>('/');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('SCN-DARK-001');

  // Sync route with URL hash on mount & hashchange
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') || '/';
      if (hash.startsWith('/ops/case/')) {
        const caseId = hash.replace('/ops/case/', '');
        setSelectedScenarioId(caseId);
        setCurrentRoute('/ops');
      } else {
        setCurrentRoute(hash);
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (route: string, scenarioId?: string) => {
    if (scenarioId) {
      setSelectedScenarioId(scenarioId);
      window.location.hash = `/ops/case/${scenarioId}`;
    } else {
      window.location.hash = route;
    }
    setCurrentRoute(route);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#070B14] text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
      <Navbar currentRoute={currentRoute} onNavigate={(r) => navigateTo(r)} />

      <main className="flex-1 flex flex-col">
        {currentRoute === '/' && (
          <Showcase onLaunchOps={(id) => navigateTo('/ops', id)} />
        )}
        {currentRoute === '/ops' && (
          <Operations initialScenarioId={selectedScenarioId} />
        )}
        {currentRoute === '/audit' && <AuditLedger />}
        {currentRoute === '/methodology' && <Methodology />}
        {currentRoute === '/dev' && <DevPlayground />}
      </main>
    </div>
  );
}

export default App;
