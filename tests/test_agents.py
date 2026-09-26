"""Unit and Integration Tests for Pillar 2 LangGraph Agentic System.
Verifies:
1. Normal graph execution and deterministic node ordering
2. Execution trace logging at every agent node
3. Feature engineering population on state
4. Sanctions screening execution
5. High-risk dark vessel and sanctions cases trigger Human-in-the-Loop review
6. Missing AIS data produces graceful degradation without crashing
7. Unavailable sanctions database falls back cleanly to degraded baseline
8. Final report structure contains concrete evidence references and citations
9. Interactive LangGraph MemorySaver checkpointing and interrupt resumption
"""

import unittest
from datetime import datetime, timezone
from langgraph.checkpoint.memory import MemorySaver

from src.schemas.mission import Mission, BoundingBox
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation, AISGap
from src.schemas.state import MaritimeAgentState
from src.agents.graph import build_maritime_intelligence_graph


class TestMaritimeAgents(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.bbox = BoundingBox(min_lat=12.0, max_lat=24.0, min_lon=58.0, max_lon=74.0)
        self.mission = Mission(
            mission_id="MSN-TEST-001",
            name="Arabian Sea Surveillance Patrol",
            time_window_start=self.now,
            time_window_end=self.now,
            bbox=self.bbox
        )

        # Standard commercial vessel with active AIS
        self.benign_sar = SARDetection(
            detection_id="SAR-DET-BENIGN-01",
            scene_id="S1A_SCENE_001",
            timestamp=self.now,
            latitude=18.95,
            longitude=72.80, # Off Mumbai
            length_m=110.0,
            width_m=20.0,
            aspect_ratio=5.5,
            heading_deg=180.0,
            confidence=0.95
        )

        self.benign_ais = AISObservation(
            mmsi="419000123",
            timestamp=self.now,
            latitude=18.95,
            longitude=72.80,
            sog=11.2,
            cog=180.0,
            vessel_name="INDIAN STAR",
            ship_type="Cargo"
        )

        # Suspicious dark tanker in deep international waters / STS zone
        self.dark_sar = SARDetection(
            detection_id="SAR-DET-DARK-02",
            scene_id="S1A_SCENE_002",
            timestamp=self.now,
            latitude=19.34,
            longitude=62.11,
            length_m=185.0, # Large commercial tanker
            width_m=32.0,
            aspect_ratio=5.78,
            heading_deg=245.0,
            confidence=0.91
        )

    def test_normal_graph_execution(self):
        """Verifies end-to-end execution of benign correlated vessel scenario."""
        graph = build_maritime_intelligence_graph()
        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.benign_sar,
            matched_ais_observation=self.benign_ais
        )

        result = graph.invoke(initial_state)

        # 1. State integrity
        self.assertIsNotNone(result.get("engineered_features"))
        self.assertIsNotNone(result.get("risk_assessment"))
        self.assertIsNotNone(result.get("final_report"))
        self.assertIsNotNone(result.get("sanctions_result"))

        # 2. Node ordering & execution trace
        trace = result["execution_trace"]
        self.assertGreaterEqual(len(trace), 5)
        agent_names = [t.agent_name for t in trace]
        self.assertIn("MissionController", agent_names)
        self.assertIn("SARAISCorrelator", agent_names)
        self.assertIn("FeatureEngineerNode", agent_names)
        self.assertIn("SanctionsScreenerNode", agent_names)
        self.assertIn("ForensicAssessorNode", agent_names)
        self.assertIn("ReportPreparerNode", agent_names)

        # 3. Benign scenario should not trigger high risk HITL
        self.assertFalse(result.get("human_in_the_loop_flag", False))
        self.assertEqual(result["risk_assessment"].dark_vessel_classification, "CORRELATED_BENIGN")

    def test_high_risk_dark_vessel_triggers_hitl(self):
        """Verifies that an unmatched large commercial hull triggers the Human-in-the-Loop flag."""
        graph = build_maritime_intelligence_graph()
        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.dark_sar,
            matched_ais_observation=None # Dark vessel
        )

        result = graph.invoke(initial_state)

        # Should be classified as deliberate dark evasion
        risk = result["risk_assessment"]
        self.assertEqual(risk.dark_vessel_classification, "DELIBERATE_DARK_EVASION")
        self.assertGreaterEqual(risk.dark_vessel_probability, 0.70)

        # High risk must trigger human-in-the-loop flag and route through HumanReviewNode
        self.assertTrue(result.get("human_in_the_loop_flag"))
        agent_names = [t.agent_name for t in result["execution_trace"]]
        self.assertIn("HumanReviewNode", agent_names)
        self.assertIsNotNone(result.get("human_feedback"))

    def test_missing_ais_graceful_degradation(self):
        """Verifies that absence of AIS telemetry degrades gracefully without crashing."""
        graph = build_maritime_intelligence_graph()
        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.dark_sar,
            matched_ais_observation=None
        )

        result = graph.invoke(initial_state)

        # Degradation note must be recorded
        degradations = result.get("degradation_notes", [])
        self.assertTrue(any("AIS telemetry" in d or "dark vessel" in d for d in degradations))

        # Trace must mark SARAISCorrelator as DEGRADED
        correlator_trace = [t for t in result["execution_trace"] if t.agent_name == "SARAISCorrelator"][0]
        self.assertEqual(correlator_trace.status, "DEGRADED")

        # System still outputs a complete, validated intelligence report
        self.assertIsNotNone(result.get("final_report"))
        self.assertIn("NON_TRANSMITTING", result["final_report"].ais_status_summary)

    def test_unavailable_sanctions_degradation(self):
        """Verifies that when sanctions service is simulated offline, graph falls back gracefully."""
        graph = build_maritime_intelligence_graph()
        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.benign_sar,
            matched_ais_observation=self.benign_ais,
            degradation_notes=["sanctions_offline_simulated"]
        )

        result = graph.invoke(initial_state)

        # Sanctions screener should record degraded status
        sanctions_trace = [t for t in result["execution_trace"] if t.agent_name == "SanctionsScreenerNode"][0]
        self.assertEqual(sanctions_trace.status, "DEGRADED")

        # Sanctions result must exist with fallback notes
        sanctions_res = result.get("sanctions_result")
        self.assertIsNotNone(sanctions_res)
        self.assertIn("DEGRADED_MODE", sanctions_res.screening_notes)

        # Graph completes successfully to final report
        self.assertIsNotNone(result.get("final_report"))

    def test_structured_report_evidence_grounding(self):
        """Verifies that final IntelligenceReport contains concrete evidence references and statutes."""
        graph = build_maritime_intelligence_graph()
        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.dark_sar,
            matched_ais_observation=None
        )

        result = graph.invoke(initial_state)
        report = result["final_report"]

        # 1. Exact detection ID referenced
        self.assertEqual(report.target_detection_id, self.dark_sar.detection_id)

        # 2. Hull dimensions and radar metrics cited
        self.assertIn("185.0", report.vessel_characteristics_summary)

        # 3. Statutory citations included for commercial dark vessel
        self.assertTrue(any("SOLAS" in s for s in report.statutory_violations))

        # 4. Actionable operational recommendations
        self.assertGreater(len(report.actionable_recommendations), 0)

        # 5. Predictive waypoints generated
        self.assertGreater(len(report.predictive_forecast.extrapolated_waypoints), 0)

    def test_memory_saver_checkpoint_and_interrupt(self):
        """Verifies LangGraph MemorySaver interrupt breakpoint before HumanReviewNode for high-risk targets."""
        checkpointer = MemorySaver()
        graph = build_maritime_intelligence_graph(
            checkpointer=checkpointer,
            interrupt_on_high_risk=True
        )

        initial_state = MaritimeAgentState(
            mission=self.mission,
            active_detection=self.dark_sar,
            matched_ais_observation=None
        )

        config = {"configurable": {"thread_id": "mission-thread-001"}}

        # First invocation should pause right before HumanReviewNode
        interrupted_state = graph.invoke(initial_state, config=config)
        state_snapshot = graph.get_state(config)

        # Verify execution paused at breakpoint
        self.assertEqual(state_snapshot.next, ("HumanReviewNode",))

        # Operator supplies review feedback and resumes workflow
        graph.update_state(
            config,
            {"human_feedback": "OPERATOR_CONFIRMED: Visual verification requested via coast guard asset."}
        )

        resumed_result = graph.invoke(None, config=config)

        # Verify completed after resumption
        self.assertIsNotNone(resumed_result.get("final_report"))
        final_trace = resumed_result["execution_trace"]
        self.assertTrue(any(t.agent_name == "HumanReviewNode" for t in final_trace))
        self.assertTrue(any(t.agent_name == "ReportPreparerNode" for t in final_trace))


if __name__ == "__main__":
    unittest.main()
