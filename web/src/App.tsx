import { Suspense, lazy, Component, type ReactNode } from 'react';
import { HashRouter, Routes, Route, Navigate, Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Showcase } from './routes/Showcase';
import { useLenis } from './lib/useLenis';

const Operations = lazy(() => import('./routes/Operations').then((m) => ({ default: m.Operations })));
const AuditLedger = lazy(() => import('./routes/AuditLedger').then((m) => ({ default: m.AuditLedger })));
const Methodology = lazy(() => import('./routes/Methodology').then((m) => ({ default: m.Methodology })));
const Cases = lazy(() => import('./routes/Cases').then((m) => ({ default: m.Cases })));
const SarLab = lazy(() => import('./routes/SarLab').then((m) => ({ default: m.SarLab })));
const Screening = lazy(() => import('./routes/Screening').then((m) => ({ default: m.Screening })));
const DevPlayground = lazy(() => import('./routes/DevPlayground').then((m) => ({ default: m.DevPlayground })));

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-xl p-12 text-center">
          <h2 className="font-display text-2xl font-semibold">Something went wrong</h2>
          <p className="mt-2 text-sm text-slate-400">{this.state.error.message}</p>
          <button
            onClick={() => location.reload()}
            className="mt-6 rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const Loading = () => (
  <div className="flex flex-1 items-center justify-center p-24 text-sm text-slate-400">Loading…</div>
);

const NotFound = () => (
  <div className="mx-auto max-w-xl p-24 text-center">
    <p className="font-mono text-sm text-cyan-400">404</p>
    <h2 className="mt-2 font-display text-3xl font-semibold">Page not found</h2>
    <Link to="/" className="mt-6 inline-block text-cyan-400 underline">
      Back to the briefing
    </Link>
  </div>
);

const OpsRoute = () => {
  const { caseId } = useParams();
  return <Operations initialScenarioId={caseId ?? 'SCN-DARK-001'} />;
};

function Shell() {
  const loc = useLocation();
  const navigate = useNavigate();
  const isHome = loc.pathname === '/';
  useLenis(isHome);

  return (
    <div className="flex min-h-dvh flex-col bg-[#070B14] text-slate-100">
      <Navbar />
      <main className="flex flex-1 flex-col">
        <ErrorBoundary>
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/" element={<Showcase onLaunchOps={(id) => navigate(id ? `/ops/case/${id}` : '/ops')} />} />
              <Route path="/ops" element={<OpsRoute />} />
              <Route path="/ops/case/:caseId" element={<OpsRoute />} />
              <Route path="/cases" element={<Cases />} />
              <Route path="/sar-lab" element={<SarLab />} />
              <Route path="/screening" element={<Screening />} />
              <Route path="/audit" element={<AuditLedger />} />
              <Route path="/methodology" element={<Methodology />} />
              {import.meta.env.DEV && <Route path="/dev" element={<DevPlayground />} />}
              <Route path="/operations" element={<Navigate to="/ops" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  );
}

export function App() {
  return (
    <HashRouter>
      <Shell />
    </HashRouter>
  );
}

export default App;
