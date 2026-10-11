/**
 * Typed API Client for DVD-MDA Backend Server
 */

export type ProvenanceTag = 'REAL' | 'DERIVED' | 'SYNTHETIC' | 'HEURISTIC' | 'UNAVAILABLE';

export interface SARDetection {
  detection_id: string;
  scene_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  length_m: number;
  width_m: number;
  aspect_ratio: number;
  heading_deg?: number;
  confidence: number;
  sensor?: string;
  polarization?: string;
  target_clutter_ratio_db?: number;
}

export interface AISObservation {
  mmsi: string;
  imo?: string;
  vessel_name?: string;
  ship_type?: string;
  latitude: number;
  longitude: number;
  sog: number;
  cog: number;
  heading?: number;
  timestamp: string;
}

export interface AISGap {
  mmsi: string;
  gap_start: string;
  gap_end?: string;
  duration_hours: number;
  start_lat: number;
  start_lon: number;
  end_lat?: number;
  end_lon?: number;
  is_suspicious?: boolean;
}

export interface ScenarioFixture {
  scenario_id: string;
  scenario_name: string;
  scenario_type: string;
  description: string;
  expected_threat_tier: string;
  expected_classification: string;
  sar_detection: SARDetection;
  ais_observation: AISObservation | null;
  historical_gaps?: AISGap[];
  provenance?: {
    radar?: ProvenanceTag;
    ais?: ProvenanceTag;
    classification?: ProvenanceTag;
    source?: string;
    imagery?: ProvenanceTag;
    note?: string;
  };
  chip_id?: string;
  all_detections?: SARDetection[];
  ground_truth?: { mmsi: string; vessel_name: string; length_m: number };
  ground_truth_ais?: AISObservation;
}

export interface AgentTraceEntry {
  step_number: number;
  agent_name: string;
  action_taken: string;
  status: 'SUCCESS' | 'DEGRADED' | 'FAILED' | 'SKIPPED' | 'APPROVED' | 'OVERRIDDEN';
  latency_ms?: number;
  timestamp: string;
  details?: Record<string, any>;
  notes?: string;
}

export interface TrajectoryPoint {
  projection_hours: number;
  projected_lat: number;
  projected_lon: number;
  uncertainty_radius_km: number;
  projected_timestamp: string;
}

export interface PredictiveForecast {
  extrapolated_waypoints: TrajectoryPoint[];
  forecast_confidence?: number;
  methodology_notes?: string;
}

export interface RiskAssessment {
  dark_vessel_probability: number;
  dark_vessel_classification: string;
  sanctions_risk_level: string;
  eez_threat_level: string;
  overall_anomaly_score: number;
  risk_factors: string[];
}

export interface IntelligenceReport {
  report_id: string;
  generated_at?: string;
  mission_id: string;
  target_detection_id: string;
  threat_tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'SEVERE';
  executive_summary: string;
  vessel_characteristics_summary: string;
  ais_status_summary: string;
  identity_attribution_summary: string;
  sanctions_findings: string;
  geospatial_eez_analysis: string;
  predictive_forecast: PredictiveForecast;
  statutory_violations: string[];
  actionable_recommendations: string[];
  analyst_confidence_statement: string;
}

export interface InvestigationResult {
  status: string;
  session_id: string;
  mission_id: string;
  human_in_the_loop_required: boolean;
  execution_trace: AgentTraceEntry[];
  risk_assessment: RiskAssessment;
  forecast: PredictiveForecast;
  final_report: IntelligenceReport | null;
  geo_context: {
    latitude: number;
    longitude: number;
    inside_eez: boolean;
    eez_country?: string;
    distance_to_coast_km: number;
    distance_to_eez_boundary_km: number;
    distance_to_sts_zone_km?: number;
    nearest_sts_zone_name?: string;
    in_coverage?: boolean;
  };
  degradation_notes: string[];
}

export interface CitationItem {
  id: string;
  title: string;
  scope: string;
  statute: string;
  link?: string;
}

export interface PlatformMeta {
  system_name: string;
  version: string;
  git_sha: string;
  model_hash: string;
  feature_count: number;
  feature_schema: Record<string, string[]>;
  citation_catalog: CitationItem[];
  provenance_legend: Record<string, string>;
  metrics: Record<string, any>;
  sanctions_publish_dates: Record<string, string>;
  eez_coverage_bbox: Record<string, any>;
  llm?: { available: boolean; mode: string | null; missing: string[] };
}

export interface AuditLedgerEntry {
  index: number;
  timestamp: string;
  action: string;
  operator: string;
  details: Record<string, any>;
  prev_hash: string;
  hash: string;
}

const BASE_URL = '';

export async function fetchMeta(): Promise<PlatformMeta> {
  const res = await fetch(`${BASE_URL}/api/meta`);
  if (!res.ok) throw new Error(`Failed to fetch metadata: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios(): Promise<ScenarioFixture[]> {
  const res = await fetch(`${BASE_URL}/api/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  return res.json();
}

export async function fetchScenario(id: string): Promise<ScenarioFixture> {
  const res = await fetch(`${BASE_URL}/api/scenarios/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch scenario ${id}: ${res.statusText}`);
  return res.json();
}

export async function fetchEEZGeoJSON(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/geospatial/eez`);
  if (!res.ok) throw new Error(`Failed to fetch EEZ GeoJSON: ${res.statusText}`);
  return res.json();
}

export async function fetchAuditLedger(): Promise<{ ledger: AuditLedgerEntry[]; total_entries: number }> {
  const res = await fetch(`${BASE_URL}/api/audit`);
  if (!res.ok) throw new Error(`Failed to fetch audit ledger: ${res.statusText}`);
  return res.json();
}

export async function runInvestigation(payload: {
  mission_id?: string;
  sar_detection: SARDetection;
  matched_ais?: AISObservation | null;
  historical_gaps?: AISGap[];
  simulate_ais_offline?: boolean;
  simulate_sanctions_offline?: boolean;
  chip_id?: string;
  scenario_id?: string;
  ground_truth?: ScenarioFixture['ground_truth'];
  ground_truth_ais?: AISObservation;
  provenance?: ScenarioFixture['provenance'];
  all_detections?: SARDetection[];
}): Promise<InvestigationResult> {
  const res = await fetch(`${BASE_URL}/api/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Investigation failed: ${errorText}`);
  }
  return res.json();
}

export async function submitHITLDecision(payload: {
  session_id: string;
  analyst_disposition: 'APPROVED' | 'REJECTED' | 'ESCALATED';
  audit_notes: string;
  override_classification?: string;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/hitl/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HITL submission failed: ${res.statusText}`);
  return res.json();
}

export interface RealCaseRow {
  chip_id: string;
  mmsi: string;
  vessel_name: string;
  vessel_type: string;
  true_length_m: number;
  latitude: number;
  longitude: number;
  acq_time: string;
}

export async function fetchRealCases(): Promise<{ total: number; source: string; cases: RealCaseRow[] }> {
  const res = await fetch(`${BASE_URL}/api/cases/real`);
  if (!res.ok) throw new Error(`Failed to load real cases: ${res.statusText}`);
  return res.json();
}

export async function fetchRealCase(chipId: string, conf = 0.35): Promise<ScenarioFixture> {
  const res = await fetch(`${BASE_URL}/api/cases/real/${encodeURIComponent(chipId)}?conf=${conf}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail);
  return res.json();
}

export interface InventoryAsset {
  id: string;
  name: string;
  provenance: ProvenanceTag;
  count?: number | null;
  unit?: string;
  size_bytes?: number;
  path: string;
  source?: string;
  details?: string;
  sha256?: string | null;
}

export async function fetchInventory(): Promise<{ assets: InventoryAsset[]; tally: Record<string, number> }> {
  const res = await fetch(`${BASE_URL}/api/data/inventory`);
  if (!res.ok) throw new Error(`Failed to load inventory: ${res.statusText}`);
  return res.json();
}

/** Downloads the exhaustive PDF dossier for a report and triggers a browser save. */
export async function downloadReportPdf(reportId: string, useLlm: boolean): Promise<{ narrative: string }> {
  const res = await fetch(`${BASE_URL}/api/report/${encodeURIComponent(reportId)}/export?format=pdf&llm=${useLlm}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail);
  const blob = await res.blob();
  const name = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '')?.[1] ?? `${reportId}.pdf`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  return { narrative: res.headers.get('X-Narrative') ?? 'RULE_BASED' };
}

export interface SavedCase {
  mission_id: string;
  created_at: string;
  report_id: string | null;
  case: string;
  is_real: boolean;
  ais_withheld: boolean;
  threat_tier: string | null;
  classification: string | null;
  probability: number | null;
  hitl_required: boolean;
  hitl_decisions: number;
  in_coverage: boolean;
  degradations: number;
}

export async function fetchSavedCases(): Promise<{ total: number; cases: SavedCase[] }> {
  const res = await fetch(`${BASE_URL}/api/cases/saved`);
  if (!res.ok) throw new Error(`Failed to load cases: ${res.statusText}`);
  return res.json();
}

export interface SanctionMatchRow {
  source_list: string;
  entity_name: string;
  matched_imo?: string | null;
  matched_mmsi?: string | null;
  flag_state?: string | null;
  sanction_programs: string[];
  designation_date?: string | null;
  match_score: number;
  match_basis: string;
  remarks?: string | null;
}

export interface SanctionsScreenResult {
  is_degraded: boolean;
  result: {
    query_target: string;
    is_sanctioned: boolean;
    overall_sanctions_risk: string;
    matches: SanctionMatchRow[];
    screened_sources: string[];
    screening_notes?: string | null;
  };
}

export async function screenVessel(q: { imo?: string; mmsi?: string; vessel_name?: string; force_offline?: boolean }): Promise<SanctionsScreenResult> {
  const res = await fetch(`${BASE_URL}/api/sanctions/screen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(q),
  });
  if (!res.ok) throw new Error(`Screening failed: ${res.statusText}`);
  return res.json();
}

export interface ResultsPayload {
  sources: { key: string; file: string; modified: string; sha256: string | null }[];
  real_ablation?: {
    timestamp: string;
    task_description: string;
    total_real_chips_analyzed: number;
    subsets: Record<string, { feature_count: number; roc_auc: number; pr_auc: number; f1_score: number; accuracy: number; balanced_accuracy: number; brier_score: number }>;
  };
  agent_scenarios?: { scenario_id: number; name: string; status: string; duration_ms: number; nodes_executed: string[]; degradation_events_count: number; hitl_interrupted: boolean; final_threat_tier: string }[];
  llm_eval?: Record<string, number | string>;
}

export async function fetchResults(): Promise<ResultsPayload> {
  const res = await fetch(`${BASE_URL}/api/results`);
  if (!res.ok) throw new Error(`Failed to load results: ${res.statusText}`);
  return res.json();
}
