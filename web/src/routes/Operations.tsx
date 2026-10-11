import { useState, useEffect, useRef } from 'react';
import {
  Play,
  ShieldAlert,
  Download,
  ChevronUp,
  ChevronDown,
  Radio,
  RefreshCw,
} from 'lucide-react';
import { ProvenanceChip } from '../components/ProvenanceChip';
import type { ScenarioFixture, InvestigationResult } from '../lib/api';
import { fetchScenarios, runInvestigation, submitHITLDecision } from '../lib/api';

interface OperationsProps {
  initialScenarioId?: string;
}

export const Operations = ({ initialScenarioId = 'SCN-DARK-001' }: OperationsProps) => {
  const [scenarios, setScenarios] = useState<ScenarioFixture[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(initialScenarioId);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioFixture | null>(null);

  // Degradation toggles
  const [cutAIS, setCutAIS] = useState(false);
  const [offlineSanctions, setOfflineSanctions] = useState(false);

  // Execution state
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [activeCenterTab, setActiveCenterTab] = useState<'map' | 'sar' | 'fusion'>('map');

  // HITL state
  const [showHITLModal, setShowHITLModal] = useState(false);
  const [hitlDisposition, setHitlDisposition] = useState<'APPROVED' | 'REJECTED' | 'ESCALATED'>('APPROVED');
  const [hitlNotes, setHitlNotes] = useState('Confirmed deliberate dark crude oil carrier. Dispatched aerial surveillance.');
  const [isSubmittingHITL, setIsSubmittingHITL] = useState(false);

  // Bottom drawer
  const [drawerOpen, setDrawerOpen] = useState(true);

  // Canvas ref for SAR chip viewer
  const chipCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    fetchScenarios().then((list) => {
      setScenarios(list);
      const initial = list.find((s) => s.scenario_id === initialScenarioId) || list[0];
      if (initial) setSelectedScenario(initial);
    });
  }, [initialScenarioId]);

  // Update selected scenario
  const handleSelectScenario = (id: string) => {
    setSelectedScenarioId(id);
    const target = scenarios.find((s) => s.scenario_id === id);
    if (target) {
      setSelectedScenario(target);
      setResult(null);
      setShowHITLModal(false);
    }
  };

  // Run multi-agent investigation pipeline
  const handleExecuteInvestigation = async () => {
    if (!selectedScenario) return;
    setIsRunning(true);
    try {
      const res = await runInvestigation({
        mission_id: `OPS-${selectedScenario.scenario_id}-${Date.now().toString().slice(-4)}`,
        sar_detection: selectedScenario.sar_detection,
        matched_ais: cutAIS ? null : selectedScenario.ais_observation,
        historical_gaps: selectedScenario.historical_gaps || [],
        simulate_ais_offline: cutAIS || selectedScenario.scenario_type === 'DEGRADED_EVIDENCE',
        simulate_sanctions_offline: offlineSanctions || selectedScenario.scenario_type === 'DEGRADED_EVIDENCE',
      });
      setResult(res);
      if (res.human_in_the_loop_required) {
        setShowHITLModal(true);
      }
    } catch (err) {
      console.error('Execution error:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // Submit HITL decision
  const handleSubmitHITL = async () => {
    if (!result?.session_id) return;
    setIsSubmittingHITL(true);
    try {
      await submitHITLDecision({
        session_id: result.session_id,
        analyst_disposition: hitlDisposition,
        audit_notes: hitlNotes,
      });
      setShowHITLModal(false);
    } catch (err) {
      console.error('HITL submission error:', err);
    } finally {
      setIsSubmittingHITL(false);
    }
  };

  // Render SAR Chip Viewer Canvas
  useEffect(() => {
    const canvas = chipCanvasRef.current;
    if (!canvas || !selectedScenario) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const det = selectedScenario.sar_detection;
    const w = canvas.width;
    const h = canvas.height;

    // Draw dark radar background with synthetic speckle noise
    ctx.fillStyle = '#070B14';
    ctx.fillRect(0, 0, w, h);

    // Random speckle noise
    const imgData = ctx.getImageData(0, 0, w, h);
    for (let i = 0; i < imgData.data.length; i += 4) {
      const noise = Math.random() * 22;
      imgData.data[i] = noise;
      imgData.data[i + 1] = noise + 4;
      imgData.data[i + 2] = noise + 10;
      imgData.data[i + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);

    // Center target coordinates
    const cx = w / 2;
    const cy = h / 2;
    const targetLen = Math.min(180, (det.length_m / 245) * 160);
    const targetBeam = Math.max(16, (det.width_m / 42) * 28);
    const angleRad = ((det.heading_deg || 0) * Math.PI) / 180;

    // Annular Clutter Guard Window
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angleRad);

    ctx.strokeStyle = 'rgba(245, 158, 11, 0.4)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(-targetLen / 2 - 25, -targetBeam / 2 - 25, targetLen + 50, targetBeam + 50);

    // Vessel Hull Bright Backscatter Mask
    ctx.fillStyle = 'rgba(0, 229, 255, 0.85)';
    ctx.shadowColor = '#00E5FF';
    ctx.shadowBlur = 15;
    ctx.fillRect(-targetLen / 2, -targetBeam / 2, targetLen, targetBeam);

    // Hull Oriented Bounding Box
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([]);
    ctx.strokeRect(-targetLen / 2, -targetBeam / 2, targetLen, targetBeam);

    ctx.restore();

    // Measurement Annotations
    ctx.fillStyle = '#00E5FF';
    ctx.font = '10px monospace';
    ctx.fillText(`L: ${det.length_m.toFixed(1)}m ±3.2m`, cx - targetLen / 2, cy - targetBeam - 12);
    ctx.fillText(`B: ${det.width_m.toFixed(1)}m ±1.5m`, cx - targetLen / 2, cy - targetBeam);
    ctx.fillStyle = '#F59E0B';
    ctx.fillText(`TCR: 16.5 dB (Target: -7.7 dB / Clutter: -24.2 dB)`, 15, h - 15);
  }, [selectedScenario, activeCenterTab]);

  return (
    <div className="flex-1 flex flex-col bg-[#070B14] text-slate-100 overflow-hidden font-sans">
      {/* ------------------------------------------------------------------- */}
      {/* TACTICAL SUB-BAR */}
      {/* ------------------------------------------------------------------- */}
      <div className="h-11 px-4 border-b border-slate-800 bg-[#0C1424] flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="text-cyan-400 font-bold">CASE: {selectedScenarioId}</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-300 truncate max-w-sm">{selectedScenario?.scenario_name}</span>
          <ProvenanceChip provenance={selectedScenario?.provenance?.radar || 'DERIVED'} />
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span>RADAR: 10m/px C-BAND</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => window.open(`/api/report/${result?.final_report?.report_id || selectedScenarioId}/export?format=html`, '_blank')}
              disabled={!result}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 border border-slate-700"
            >
              <Download className="w-3 h-3 text-cyan-400" />
              <span>EXPORT BULLETIN</span>
            </button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* MAIN 3-COLUMN TACTICAL CONSOLE */}
      {/* ------------------------------------------------------------------- */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* ================================================================= */}
        {/* LEFT COLUMN: SCENARIOS & DEGRADATION TOGGLES (3 cols) */}
        {/* ================================================================= */}
        <aside className="lg:col-span-3 border-r border-slate-800 bg-[#070B14] p-4 flex flex-col gap-4 overflow-y-auto">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                SURVEILLANCE SCENARIOS
              </span>
              <span className="text-[10px] font-mono text-cyan-400">{scenarios.length} AVAILABLE</span>
            </div>

            <div className="space-y-2">
              {scenarios.map((s) => (
                <div
                  key={s.scenario_id}
                  onClick={() => handleSelectScenario(s.scenario_id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedScenarioId === s.scenario_id
                      ? 'bg-cyan-950/40 border-cyan-500/50 shadow-[0_0_15px_rgba(0,229,255,0.15)]'
                      : 'bg-[#0C1424] border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                    <span className="text-cyan-400 font-bold">{s.scenario_id}</span>
                    <ProvenanceChip provenance={s.provenance?.radar || 'DERIVED'} />
                  </div>
                  <div className="font-bold text-xs text-white">{s.scenario_name}</div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{s.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Degradation Controls */}
          <div className="p-4 rounded-xl bg-[#0C1424] border border-slate-800">
            <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider block mb-3">
              COUNTERFACTUAL DEGRADATION
            </span>

            <div className="space-y-3 text-xs">
              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <div className="text-slate-200 font-semibold">Sever AIS Feed</div>
                  <div className="text-[10px] text-slate-500">Simulates satellite transponder loss</div>
                </div>
                <input
                  type="checkbox"
                  checked={cutAIS}
                  onChange={(e) => setCutAIS(e.target.checked)}
                  className="w-4 h-4 accent-amber-400 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <div>
                  <div className="text-slate-200 font-semibold">Offline Sanctions DB</div>
                  <div className="text-[10px] text-slate-500">Forces fallback rule baseline</div>
                </div>
                <input
                  type="checkbox"
                  checked={offlineSanctions}
                  onChange={(e) => setOfflineSanctions(e.target.checked)}
                  className="w-4 h-4 accent-amber-400 cursor-pointer"
                />
              </label>
            </div>
          </div>

          {/* Primary Action Button */}
          <button
            onClick={handleExecuteInvestigation}
            disabled={isRunning}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-600 hover:from-cyan-300 hover:to-blue-500 text-slate-950 font-bold text-xs tracking-wider uppercase flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(0,229,255,0.3)] transition-all disabled:opacity-50 active:scale-95"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Multi-Agent Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-slate-950" />
                <span>Execute Autonomous Pipeline</span>
              </>
            )}
          </button>
        </aside>

        {/* ================================================================= */}
        {/* CENTER COLUMN: DUAL TACTICAL DISPLAY (6 cols) */}
        {/* ================================================================= */}
        <main className="lg:col-span-6 flex flex-col border-r border-slate-800 bg-[#070B14]">
          {/* Tab Bar */}
          <div className="h-10 px-4 border-b border-slate-800 bg-[#0C1424]/60 flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveCenterTab('map')}
                className={`px-3 py-1.5 rounded-md ${
                  activeCenterTab === 'map'
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                TACTICAL CHART
              </button>
              <button
                onClick={() => setActiveCenterTab('sar')}
                className={`px-3 py-1.5 rounded-md ${
                  activeCenterTab === 'sar'
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                SAR CHIP INSPECTOR
              </button>
              <button
                onClick={() => setActiveCenterTab('fusion')}
                className={`px-3 py-1.5 rounded-md ${
                  activeCenterTab === 'fusion'
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                FUSION METRICS
              </button>
            </div>

            <ProvenanceChip provenance="DERIVED" source="WGS-84 Projection" />
          </div>

          {/* Display Viewport */}
          <div className="flex-1 relative bg-[#070B14] overflow-hidden flex items-center justify-center">
            {activeCenterTab === 'map' && (
              <div className="w-full h-full p-4 flex flex-col justify-between relative bg-radial-at-c from-[#0C1424] to-[#070B14]">
                {/* Simulated Tactical Ocean Overlay */}
                <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#00E5FF 1px, transparent 1px)', backgroundSize: '32px 32px' }} />

                <div className="relative z-10 flex items-center justify-between text-xs font-mono">
                  <div className="p-2 rounded bg-[#070B14]/80 border border-slate-800">
                    <span className="text-slate-500">REGION:</span>{' '}
                    <span className="text-cyan-400 font-bold">ARABIAN SEA BASIN (UNCLOS EEZ)</span>
                  </div>
                  <div className="p-2 rounded bg-[#070B14]/80 border border-slate-800 text-slate-400">
                    LAT: {selectedScenario?.sar_detection.latitude.toFixed(4)}° N | LON: {selectedScenario?.sar_detection.longitude.toFixed(4)}° E
                  </div>
                </div>

                {/* Tactical Target Indicator */}
                <div className="relative z-10 m-auto text-center">
                  <div className="relative inline-block">
                    <div className="w-24 h-24 rounded-full border-2 border-dashed border-cyan-400/60 animate-spin" style={{ animationDuration: '20s' }} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-4 h-4 rounded-full bg-rose-500 shadow-[0_0_15px_#EF4444] animate-pulse" />
                    </div>
                  </div>
                  <div className="mt-3 font-mono text-xs text-cyan-300 font-bold">
                    TARGET: {selectedScenario?.sar_detection.detection_id}
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    EST. LENGTH: {selectedScenario?.sar_detection.length_m}m | BEARING: {selectedScenario?.sar_detection.heading_deg}°
                  </div>

                  {/* Dead-Reckoning Uncertainty Cones */}
                  <div className="mt-6 flex items-center justify-center gap-3 text-[10px] font-mono">
                    <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                      +6h Cone: ±12.4 km
                    </span>
                    <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                      +12h Cone: ±26.8 km
                    </span>
                    <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                      +24h Cone: ±58.2 km
                    </span>
                  </div>
                </div>

                <div className="relative z-10 text-[10px] font-mono text-slate-500 flex items-center justify-between">
                  <span>UNCLOS SOVEREIGN BORDERS: INDIA • PAKISTAN • OMAN</span>
                  <span>DATUM: EPSG:4326 (WGS84)</span>
                </div>
              </div>
            )}

            {activeCenterTab === 'sar' && (
              <div className="w-full h-full flex flex-col items-center justify-center p-6">
                <canvas
                  ref={chipCanvasRef}
                  width={420}
                  height={320}
                  className="rounded-xl border border-cyan-500/30 shadow-[0_0_30px_rgba(0,0,0,0.8)]"
                />
                <div className="mt-4 text-xs font-mono text-slate-400 text-center">
                  SENTINEL-1 C-SAR DUAL-POL CHIP • ORIENTED MINIMUM-AREA RECTANGLE
                </div>
              </div>
            )}

            {activeCenterTab === 'fusion' && (
              <div className="w-full h-full p-6 overflow-y-auto font-mono text-xs">
                <h4 className="text-cyan-400 font-bold mb-4 uppercase">SAR-AIS SPATIO-TEMPORAL FUSION BREAKDOWN</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-[#0C1424] border border-slate-800">
                    <div className="text-slate-500">SPATIAL DISTANCE</div>
                    <div className="text-lg text-white font-bold mt-1">
                      {cutAIS ? 'UNMATCHED' : selectedScenario?.ais_observation ? '0.12 km' : '280.4 km (OUTAGE)'}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0C1424] border border-slate-800">
                    <div className="text-slate-500">TEMPORAL DELTA</div>
                    <div className="text-lg text-white font-bold mt-1">
                      {cutAIS ? 'N/A' : selectedScenario?.ais_observation ? '1.0 min' : '48.0 hrs (DARK)'}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0C1424] border border-slate-800">
                    <div className="text-slate-500">CORRELATION STATUS</div>
                    <div className="text-lg text-cyan-400 font-bold mt-1">
                      {cutAIS || !selectedScenario?.ais_observation ? 'NON_TRANSMITTING' : 'POSITIVELY_MATCHED'}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0C1424] border border-slate-800">
                    <div className="text-slate-500">PROBABILITY RATING</div>
                    <div className="text-lg text-amber-400 font-bold mt-1">
                      {result?.risk_assessment?.dark_vessel_probability ? `${(result.risk_assessment.dark_vessel_probability * 100).toFixed(0)}%` : '98%'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* ================================================================= */}
        {/* RIGHT COLUMN: 7-NODE LANGGRAPH AGENTIC TRACE (3 cols) */}
        {/* ================================================================= */}
        <aside className="lg:col-span-3 border-l border-slate-800 bg-[#070B14] p-4 flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              LANGGRAPH AGENT TRACE
            </span>
            <span className="text-[10px] font-mono text-emerald-400">MEMORYSAVER ACTIVE</span>
          </div>

          {/* Trace Timeline */}
          <div className="space-y-2">
            {(result?.execution_trace || [
              { step_number: 1, agent_name: 'MissionController', status: 'SUCCESS', latency_ms: 12.4, notes: 'Telemetry ingested' },
              { step_number: 2, agent_name: 'SARAISCorrelator', status: 'SUCCESS', latency_ms: 18.2, notes: 'Spatial match computed' },
              { step_number: 3, agent_name: 'FeatureEngineerNode', status: 'SUCCESS', latency_ms: 24.1, notes: 'Feature vector extracted' },
              { step_number: 4, agent_name: 'SanctionsScreenerNode', status: 'SUCCESS', latency_ms: 0.8, notes: 'OFAC/UN verified' },
              { step_number: 5, agent_name: 'ForensicAssessorNode', status: 'SUCCESS', latency_ms: 14.6, notes: 'Risk assessment rated' },
              { step_number: 6, agent_name: 'HumanReviewNode', status: 'APPROVED', latency_ms: 8.5, notes: 'Analyst review gate' },
              { step_number: 7, agent_name: 'ReportPreparerNode', status: 'SUCCESS', latency_ms: 31.0, notes: 'Bulletin compiled' },
            ]).map((step) => (
              <div key={step.step_number} className="p-3 rounded-lg bg-[#0C1424] border border-slate-800 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold">0{step.step_number} • {step.agent_name}</span>
                  <span className="text-[10px] text-emerald-400 font-bold">{step.status}</span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                  <span>{step.notes || 'Execution nominal'}</span>
                  <span>{step.latency_ms?.toFixed(1) || '15.0'} ms</span>
                </div>
              </div>
            ))}
          </div>

          {result?.human_in_the_loop_required && (
            <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/40 text-xs">
              <div className="flex items-center gap-2 text-amber-400 font-bold font-mono">
                <ShieldAlert className="w-4 h-4" />
                <span>HITL INTERRUPT TRIGGERED</span>
              </div>
              <p className="text-[11px] text-slate-300 mt-1">
                High-risk dark vessel hypothesis exceeds sovereign interdiction thresholds.
              </p>
              <button
                onClick={() => setShowHITLModal(true)}
                className="mt-3 w-full py-1.5 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold font-mono text-[11px]"
              >
                OPEN DISPOSITION MODAL
              </button>
            </div>
          )}
        </aside>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* BOTTOM DRAWER: INTELLIGENCE BULLETIN */}
      {/* ------------------------------------------------------------------- */}
      <footer className="border-t border-slate-800 bg-[#0C1424] text-xs font-mono">
        <div
          onClick={() => setDrawerOpen(!drawerOpen)}
          className="h-9 px-4 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 border-b border-slate-800/60"
        >
          <div className="flex items-center gap-3">
            <span className="font-bold text-slate-200 uppercase">
              STRUCTURED INTELLIGENCE BULLETIN
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                result?.final_report?.threat_tier === 'SEVERE' || selectedScenario?.expected_threat_tier === 'CRITICAL'
                  ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                  : 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
              }`}
            >
              THREAT TIER: {result?.final_report?.threat_tier || selectedScenario?.expected_threat_tier || 'HIGH'}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-400">
            <span>{drawerOpen ? 'COLLAPSE DRAWER' : 'EXPAND BULLETIN'}</span>
            {drawerOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </div>
        </div>

        {drawerOpen && (
          <div className="p-6 max-h-60 overflow-y-auto grid grid-cols-1 md:grid-cols-3 gap-6 bg-[#070B14]/80">
            <div>
              <h5 className="text-amber-400 font-bold uppercase mb-2">EXECUTIVE SUMMARY</h5>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                {result?.final_report?.executive_summary ||
                  `Autonomous Maritime Intelligence Bulletin for target ${selectedScenario?.sar_detection.detection_id}. Unidentified dark commercial hull (${selectedScenario?.sar_detection.length_m}m) in deep offshore international waters with zero active AIS signals.`}
              </p>
            </div>

            <div>
              <h5 className="text-cyan-400 font-bold uppercase mb-2">STATUTORY CITATIONS</h5>
              <div className="flex flex-wrap gap-1.5">
                {(result?.final_report?.statutory_violations || [
                  'SOLAS Ch. V Reg. 19',
                  'UNCLOS Art. 73',
                  'OFAC IEEPA',
                ]).map((statute, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 text-[10px]">
                    {statute}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h5 className="text-emerald-400 font-bold uppercase mb-2">ACTIONABLE RECOMMENDATIONS</h5>
              <ul className="text-slate-300 text-[11px] space-y-1 list-disc list-inside">
                {(result?.final_report?.actionable_recommendations || [
                  'File urgent IFC-IOR suspicious maritime incident report.',
                  'Dispatch Coast Guard patrol aircraft for optical and FLIR verification.',
                  'Alert regional naval task force for possible STS interdiction.',
                ]).map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </footer>

      {/* ------------------------------------------------------------------- */}
      {/* HITL OPERATOR MODAL */}
      {/* ------------------------------------------------------------------- */}
      {showHITLModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-2xl glass-panel-elevated border border-amber-500/50 shadow-[0_0_50px_rgba(245,158,11,0.2)]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
                <h3 className="font-display font-bold text-lg text-white">OPERATOR HITL REVIEW CHECKPOINT</h3>
              </div>
              <button onClick={() => setShowHITLModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <p className="mt-3 text-xs text-slate-300 leading-relaxed">
              LangGraph has halted at <strong>HumanReviewNode</strong>. The target satisfies high-probability deliberate dark evasion or sanctions criteria. Submit your authoritative audit disposition:
            </p>

            <div className="mt-4 space-y-2 text-xs font-mono">
              <label className="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800 cursor-pointer">
                <input
                  type="radio"
                  name="hitl_disp"
                  checked={hitlDisposition === 'APPROVED'}
                  onChange={() => setHitlDisposition('APPROVED')}
                  className="accent-amber-400"
                />
                <span className="text-emerald-400 font-bold">CONFIRM & ESCALATE TO COAST GUARD</span>
              </label>

              <label className="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800 cursor-pointer">
                <input
                  type="radio"
                  name="hitl_disp"
                  checked={hitlDisposition === 'REJECTED'}
                  onChange={() => setHitlDisposition('REJECTED')}
                  className="accent-amber-400"
                />
                <span className="text-rose-400 font-bold">REJECT AS FALSE POSITIVE</span>
              </label>
            </div>

            <div className="mt-4">
              <label className="block text-xs font-mono text-slate-400 mb-1">MANDATORY AUDIT LOGGING NOTES:</label>
              <textarea
                value={hitlNotes}
                onChange={(e) => setHitlNotes(e.target.value)}
                className="w-full h-20 p-2.5 rounded-lg bg-[#070B14] border border-slate-700 text-xs font-mono text-slate-200 focus:border-cyan-400 outline-none"
              />
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowHITLModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitHITL}
                disabled={isSubmittingHITL}
                className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs font-mono tracking-wider transition-colors"
              >
                {isSubmittingHITL ? 'Committing...' : 'Commit to Audit Ledger'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
