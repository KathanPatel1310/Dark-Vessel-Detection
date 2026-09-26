# Phase 8 & 9 Agentic AI Architecture, Execution, and Quality Assessment Report

**Execution Timestamp**: 2026-09-26T22:40:55+05:30  
**Audit Script**: `scripts/run_agent_scenarios.py`  
**Results Data**: [agent_scenario_results.json](file:///c:/Users/katha/College/Sem%205/DKU%20Project/reports/agent_scenario_results.json)  
**Orchestration Engine**: LangGraph (`StateGraph`, `MemorySaver`, Pregel Stream Engine)  

---

## 1. 10-Scenario Empirical Execution Results

| Scenario ID & Name | Input Condition | Nodes Executed | Degradation Events | HITL Triggered | HITL Resumed | Latency | Result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **01. Normal Correlated Vessel** | Active matching AIS broadcast | 6 nodes | 0 | False | N/A | 835.2 ms* | **PASSED** |
| **02. Unmatched Dark Vessel** | 185m tanker, zero AIS pings | 7 nodes | 1 | **True** | **True** | 7.3 ms | **PASSED** |
| **03. Missing AIS** | Completely empty AIS track list | 7 nodes | 1 | **True** | **True** | 7.3 ms | **PASSED** |
| **04. Sanctions Match** | IMO 9187629 in OFAC database | 6 nodes | 0 | False (Direct) | N/A | 6.4 ms | **PASSED** |
| **05. Sanctions Unavailable** | Outage injected in registry | 7 nodes | 2 | **True** | **True** | 8.5 ms | **PASSED** |
| **06. Missing Geospatial Data** | Unmapped South Ocean coordinates | 7 nodes | 1 | **True** | **True** | 7.4 ms | **PASSED** |
| **07. High-Risk Case (HITL)** | Large tanker near STS corridor | 7 nodes | 1 | **True** | **True** | 8.1 ms | **PASSED** |
| **08. Low-Risk Case (Bypass)** | 22m coastal craft (exempt) | 6 nodes | 0 | False (Bypassed)| N/A | 5.5 ms | **PASSED** |
| **09. Malformed Input** | Extreme coords, 0.0 TCR | 7 nodes | 1 | **True** | **True** | 7.1 ms | **PASSED** |
| **10. Candidate AIS Matches** | Anchorage density evaluation | 6 nodes | 0 | False | N/A | 5.6 ms | **PASSED** |

*\*Note: Scenario 1 latency includes one-time cold load of OFAC/UN XML database into memory ($1,563$ records).*

---

## 2. Graph Topology and State Machine Verification

```mermaid
graph TD
    START([START]) --> MissionController[1. MissionController]
    MissionController --> SARAISCorrelator[2. SARAISCorrelator]
    SARAISCorrelator --> FeatureEngineerNode[3. FeatureEngineerNode]
    FeatureEngineerNode --> SanctionsScreenerNode[4. SanctionsScreenerNode]
    SanctionsScreenerNode --> ForensicAssessorNode[5. ForensicAssessorNode]
    
    ForensicAssessorNode -->|High Risk Flag == True| HumanReviewNode[6. HumanReviewNode<br/>(HITL Checkpoint)]
    ForensicAssessorNode -->|High Risk Flag == False| ReportPreparerNode[7. ReportPreparerNode]
    
    HumanReviewNode --> ReportPreparerNode
    ReportPreparerNode --> END([END])
```

### Verified Structural Properties
1. **Typed State Container**:  
   State is strictly governed by `MaritimeAgentState` (`pydantic.BaseModel`), ensuring end-to-end schema conformance without untyped dictionary leakage.
2. **Conditional Routing**:  
   The conditional routing function `route_after_forensic_assessment()` dynamically inspects `human_in_the_loop_flag`. High-risk evasion triggers transition to `HumanReviewNode`; benign traffic directly transitions to `ReportPreparerNode`.
3. **Interactive Checkpoint & Interruption**:  
   Compiled with `interrupt_before=["HumanReviewNode"]` using LangGraph's `MemorySaver`. High-risk scenarios suspend execution state at the checkpoint. Resuming via `graph.stream(None, config)` restores state from disk/memory and executes `ReportPreparerNode` to completion.
4. **Resilient Degradation**:  
   When AIS or registry feeds fail, nodes append diagnostic notes to `degradation_notes` and adjust analytical priors without throwing unhandled exceptions.

---

## 3. Engineering Assessment: Is it "Agentic AI"?

To provide a scientifically rigorous evaluation for the professor:

### What IS Implemented:
- **Stateful Directed Acyclic Graph (DAG)**: Built using official LangGraph `StateGraph`.
- **Dynamic Conditional Branching**: True runtime branch selection based on computed risk scores.
- **Checkpointing and Human Intervention**: Working LangGraph Pregel interrupts with operator resumption.
- **Auditable Machine-Readable Trace**: `execution_trace` records node names, actions, timestamps, and status for full operational traceability.

### What is NOT Implemented (Honest Technical Reality):
- **Deterministic Orchestration vs. Autonomous LLM Reasoning**:  
  Currently, the nodes wrap **deterministic Python algorithms** (`RealEEZChecker`, `RealSanctionsDatabase`, `FeaturePipeline`, `MaritimeRiskScorer`). 
- There is **no LLM making dynamic decisions or tool calls** inside the live graph loop.
- The system is an **agentic workflow / stateful workflow orchestrator**, not an autonomous agent driven by an LLM reasoning loop (such as ReAct).
- This design choice is technically advantageous for safety and speed: radar physics, spatial distances, and sanctions screening should be computed deterministically rather than hallucinated by an LLM.

---

## 4. Recommendations for Professor Demonstration

1. **Demonstrate HITL Breakpoint Live**:  
   Show the terminal halting at `HumanReviewNode` for Scenario 2 (Dark Tanker) and proceeding automatically for Scenario 8 (Coastal Small Craft).
2. **Clarify Engineering Boundary**:  
   Explicitly present LangGraph as a **deterministic mission controller and safety supervisor**, emphasizing that deterministic calculation protects against catastrophic LLM arithmetic errors.
