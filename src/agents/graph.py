"""LangGraph StateGraph Workflow Orchestrator for Maritime Intelligence.
Constructs the multi-agent decision graph connecting:
1. MissionController
2. SARAISCorrelator (with graceful degradation on missing AIS)
3. FeatureEngineerNode (Pillar 1 feature engine)
4. SanctionsScreenerNode (with graceful degradation on unavailable registry)
5. ForensicAssessorNode (risk scoring, dead reckoning, and HITL detection)
6. HumanReviewNode (HITL review checkpoint)
7. ReportPreparerNode (final structured intelligence synthesis)
"""

import time
from functools import wraps
from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.schemas.state import MaritimeAgentState
from src.agents.nodes import (
    mission_controller_node,
    sar_ais_correlator_node,
    feature_engineer_node,
    sanctions_screener_node,
    forensic_assessor_node,
    human_review_node,
    report_preparer_node,
)


def _timed(fn):
    """Records the measured wall-clock latency (ms) on the trace entry the node just appended."""
    @wraps(fn)
    def wrapper(state):
        start = time.perf_counter()
        out = fn(state)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        trace = out.get("execution_trace") if isinstance(out, dict) else None
        if trace:
            last = trace[-1]
            if getattr(last, "latency_ms", None) is None:
                try:
                    last.latency_ms = elapsed_ms
                except Exception:
                    pass
        return out
    return wrapper


def route_after_forensic_assessment(state: MaritimeAgentState) -> str:
    """
    Conditional routing edge evaluating whether Human-in-the-Loop review is required.
    Routes to 'HumanReviewNode' if high risk is flagged, else proceeds to 'ReportPreparerNode'.
    """
    # Note: state can be dict or MaritimeAgentState depending on LangGraph version
    hitl_flag = getattr(state, "human_in_the_loop_flag", None)
    if hitl_flag is None and isinstance(state, dict):
        hitl_flag = state.get("human_in_the_loop_flag", False)

    if hitl_flag:
        return "HumanReviewNode"
    return "ReportPreparerNode"


def build_maritime_intelligence_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_on_high_risk: bool = False
):
    """
    Builds and compiles the production LangGraph StateGraph.

    Args:
        checkpointer: Optional LangGraph checkpoint saver (e.g. MemorySaver).
                      Required if interrupt_on_high_risk=True.
        interrupt_on_high_risk: If True, registers an explicit breakpoint before
                                'HumanReviewNode' to pause execution until analyst resumption.

    Returns:
        Compiled LangGraph Pregel application.
    """
    builder = StateGraph(MaritimeAgentState)

    # 1. Add all 6 primary nodes + HITL review node
    builder.add_node("MissionController", _timed(mission_controller_node))
    builder.add_node("SARAISCorrelator", _timed(sar_ais_correlator_node))
    builder.add_node("FeatureEngineerNode", _timed(feature_engineer_node))
    builder.add_node("SanctionsScreenerNode", _timed(sanctions_screener_node))
    builder.add_node("ForensicAssessorNode", _timed(forensic_assessor_node))
    builder.add_node("HumanReviewNode", _timed(human_review_node))
    builder.add_node("ReportPreparerNode", _timed(report_preparer_node))

    # 2. Add deterministic processing edges
    builder.add_edge(START, "MissionController")
    builder.add_edge("MissionController", "SARAISCorrelator")
    builder.add_edge("SARAISCorrelator", "FeatureEngineerNode")
    builder.add_edge("FeatureEngineerNode", "SanctionsScreenerNode")
    builder.add_edge("SanctionsScreenerNode", "ForensicAssessorNode")

    # 3. Add conditional routing edge for Human-in-the-Loop gate
    builder.add_conditional_edges(
        "ForensicAssessorNode",
        route_after_forensic_assessment,
        {
            "HumanReviewNode": "HumanReviewNode",
            "ReportPreparerNode": "ReportPreparerNode"
        }
    )

    # 4. Convergence edges
    builder.add_edge("HumanReviewNode", "ReportPreparerNode")
    builder.add_edge("ReportPreparerNode", END)

    # 5. Compile with optional interrupt breakpoint
    interrupt_nodes = ["HumanReviewNode"] if (interrupt_on_high_risk and checkpointer) else None

    compiled_graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_nodes
    )

    return compiled_graph
