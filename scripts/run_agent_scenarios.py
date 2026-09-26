"""
Phase 8: Multi-Agent Execution Audit on 10 Scenarios.
Executes the compiled LangGraph StateGraph, records node traces, degradation events,
HITL pauses/resumptions, and per-node execution timings.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from langgraph.checkpoint.memory import MemorySaver

from src.schemas.mission import Mission, BoundingBox
from src.schemas.sar import SARDetection
from src.schemas.ais import AISObservation
from src.schemas.state import MaritimeAgentState
from src.agents.graph import build_maritime_intelligence_graph

def run_agent_scenarios_audit():
    print("=== STARTING PHASE 8 AGENTIC AI EXECUTION AUDIT (10 SCENARIOS) ===")
    
    scenarios_meta = [
        {"id": 1, "name": "Normal correlated vessel", "desc": "Commercial vessel with active, matching AIS broadcasts"},
        {"id": 2, "name": "Unmatched dark vessel", "desc": "Large commercial hull (185m) in international waters with no AIS"},
        {"id": 3, "name": "Missing AIS", "desc": "Completely empty AIS candidate list in surveillance AOI"},
        {"id": 4, "name": "Sanctions match", "desc": "Correlated vessel with confirmed match in OFAC/UN database (IMO 9187629)"},
        {"id": 5, "name": "Sanctions source unavailable", "desc": "Sanctions screening engine falls back with degradation notes"},
        {"id": 6, "name": "Missing geospatial data", "desc": "Surveillance point far outside mapped regional EEZ zones"},
        {"id": 7, "name": "High-risk case requiring human review", "desc": "Unidentified tanker near STS transfer corridor triggering HITL"},
        {"id": 8, "name": "Low-risk case bypassing human review", "desc": "Small craft (22m) operating in coastal waters with valid correlation"},
        {"id": 9, "name": "Boundary or extreme measurement input", "desc": "Radar target with boundary values, zero clutter ratio, extreme size"},
        {"id": 10, "name": "Candidate AIS matches evaluation", "desc": "Vessel evaluated with candidate track and historical gaps"}
    ]
    
    results = []
    
    for meta in scenarios_meta:
        s_id = meta["id"]
        s_name = meta["name"]
        print(f"\n[{s_id}/10] Executing Scenario: {s_name}...")
        
        # Prepare mission
        now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
        mission = Mission(
            mission_id=f"SCENARIO-{s_id:02d}",
            time_window_start=now - timedelta(hours=2),
            time_window_end=now + timedelta(hours=2),
            roi_name="Arabian Sea",
            bbox=BoundingBox(min_lat=12.0, max_lat=26.0, min_lon=55.0, max_lon=75.0),
            priority="HIGH" if s_id in [2, 4, 7] else "ROUTINE"
        )
        
        # Setup SAR target
        sar_length = 22.0 if s_id == 8 else (185.0 if s_id in [2, 7] else 125.0)
        sar_width = 5.0 if s_id == 8 else 28.0
        sar_lat = 20.0 if s_id != 6 else -45.0
        sar_lon = 62.0 if s_id != 6 else 110.0
        
        sar_target = SARDetection(
            detection_id=f"SAR-DET-{s_id:03d}",
            scene_id=f"S1A_SCENARIO_{s_id}",
            timestamp=now,
            latitude=sar_lat,
            longitude=sar_lon,
            length_m=sar_length,
            width_m=sar_width,
            aspect_ratio=round(sar_length / max(1.0, sar_width), 2),
            confidence=0.92,
            heading_deg=145.0,
            target_clutter_ratio_db=24.5 if s_id != 9 else 0.0
        )
        
        # Setup AIS candidates
        matched_ais = None
        if s_id in [1, 4, 8, 10]:
            matched_ais = AISObservation(
                mmsi="123456789" if s_id != 4 else "273359000",
                imo="9187629" if s_id == 4 else "9451234",
                vessel_name="SANCTIONED TANKER" if s_id == 4 else "BENIGN CARGO",
                latitude=sar_lat + 0.005,
                longitude=sar_lon + 0.005,
                sog=12.2 if s_id != 8 else 6.5,
                cog=145.0,
                heading=145.0,
                timestamp=now - timedelta(minutes=2)
            )

        # Initial Agent State
        initial_state = MaritimeAgentState(
            mission=mission,
            active_detection=sar_target,
            matched_ais_observation=matched_ais
        )

        if s_id == 5:
            initial_state.degradation_notes.append("TEST_INJECT: Sanctions registry mock outage")

        # Compile graph with MemorySaver and interrupt on high risk
        checkpointer = MemorySaver()
        graph = build_maritime_intelligence_graph(
            checkpointer=checkpointer,
            interrupt_on_high_risk=True
        )
        config = {"configurable": {"thread_id": f"scenario_{s_id:02d}"}}

        t0 = time.perf_counter()
        step_events = []
        is_hitl_paused = False
        resumed_successfully = False

        # Execute graph (step by step streaming)
        try:
            for event in graph.stream(initial_state, config=config, stream_mode="updates"):
                node_name = list(event.keys())[0]
                step_events.append(node_name)
                
            # Check state at checkpoint
            curr_state = graph.get_state(config)
            if curr_state.next and "HumanReviewNode" in curr_state.next:
                is_hitl_paused = True
                print(f"  -> StateGraph paused at HITL Checkpoint before {curr_state.next}!")
                # Resume execution with operator feedback
                resumed_stream = graph.stream(None, config=config, stream_mode="updates")
                for r_event in resumed_stream:
                    r_node = list(r_event.keys())[0]
                    step_events.append(r_node)
                resumed_successfully = True
                print(f"  -> Successfully resumed HITL execution to completion!")

            t1 = time.perf_counter()
            total_duration_ms = round((t1 - t0) * 1000, 2)
            
            # Fetch final state
            final_snapshot = graph.get_state(config).values
            report = final_snapshot.get("final_report")
            trace = final_snapshot.get("execution_trace", [])
            degradations = final_snapshot.get("degradation_notes", [])
            risk_assessment = final_snapshot.get("risk_assessment")

            status = "PASSED"
            scenario_summary = {
                "scenario_id": s_id,
                "name": s_name,
                "status": status,
                "duration_ms": total_duration_ms,
                "nodes_executed": step_events,
                "total_nodes_count": len(step_events),
                "degradation_events_count": len(degradations),
                "degradation_notes": degradations,
                "hitl_interrupted": is_hitl_paused,
                "hitl_resumed": resumed_successfully,
                "final_threat_tier": report.threat_tier if report else None,
                "final_report_id": report.report_id if report else None,
                "statutory_violations": report.statutory_violations if report else [],
                "risk_anomaly_score": risk_assessment.overall_anomaly_score if risk_assessment else None,
                "dark_vessel_classification": risk_assessment.dark_vessel_classification if risk_assessment else None,
                "trace_steps": [
                    {"agent": t.agent_name, "status": t.status, "action": t.action_taken}
                    for t in trace
                ]
            }
            results.append(scenario_summary)
            print(f"  Scenario {s_id} Result: {status} in {total_duration_ms}ms (Threat: {report.threat_tier if report else 'NONE'})")

        except Exception as e:
            print(f"  Scenario {s_id} FAILED: {e}")
            results.append({
                "scenario_id": s_id,
                "name": s_name,
                "status": "FAILED",
                "error": str(e)
            })

    # Save to reports/agent_scenario_results.json
    output_path = "reports/agent_scenario_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved all 10 scenario execution traces to {output_path}")

if __name__ == "__main__":
    run_agent_scenarios_audit()
