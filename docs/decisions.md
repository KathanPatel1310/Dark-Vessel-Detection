# Architectural Decision Records (ADRs)

## ADR-001: Replacement of SciHub / sentinelsat with CDSE & GFW SAR APIs
*   **Context:** The legacy document specified `sentinelsat` connecting to `scihub.copernicus.eu`. ESA permanently closed SciHub on October 31, 2023. Scripts relying on `sentinelsat` fail immediately.
*   **Decision:** Migrate SAR data access to the new Copernicus Data Space Ecosystem (CDSE) APIs (STAC/OData) and utilize the Global Fishing Watch 4Wings SAR presence dataset (`public-global-sar-presence:latest`).
*   **Consequences:** Ensures full programmatic viability without broken legacy dependencies. Enables instantaneous spatial-temporal queries without heavy, unneeded network transfer latency.

---

## ADR-002: Decoupled Detection-Reasoning Architecture vs Two-Stage VLM (LLaVA)
*   **Context:** The original proposal suggested fine-tuning LLaVA-1.6 (or InternVL2) in two stages: Stage 1 to detect ships from SAR chips, and Stage 2 to generate textual reports.
*   **Evaluation:**
    1.  Natural image VLMs are poorly suited for microwave radar backscatter matrices.
    2.  VLM vision encoders require massive compute to fine-tune and exhibit high inference latency.
    3.  Asking a vision model to generate tabular, legal, and operational text leads to hallucinations and inefficiency.
*   **Decision:** Decouple computer vision from intelligence reasoning. Use specialized radar feature extractors / lightweight detectors (e.g. YOLO on SSDD/HRSID or CFAR backscatter algorithms) to generate structured numerical metrics (length, width, RCS, backscatter ratio), then pass these verified features to an LLM specialized in text reasoning and legal synthesis.
*   **Consequences:** Yields high compute efficiency, deterministic latency, and focuses LLM fine-tuning entirely on the primary system requirement: evidence-grounded maritime intelligence synthesis.

---

## ADR-003: Selection of Qwen 2.5 (7B / 3B) for QLoRA Fine-Tuning
*   **Context:** System Architecture Pillar 3 mandates supervised fine-tuning of an open-weight LLM on domain-specific maritime intelligence data.
*   **Comparison:**
    *   *LLaVA-1.6:* Architecturally inappropriate for structured tabular and statutory synthesis.
    *   *Llama-3.1-8B:* Strong, but requires gated licensing tokens and higher parameter overhead.
    *   *Mistral-7B-v0.3:* Good, but higher memory footprint during 4-bit SFT.
    *   *Qwen2.5-7B-Instruct (Primary):* Apache 2.0 license, state-of-the-art reasoning, exceptional JSON structure compliance, fits in ~4.5 GB in 4-bit.
    *   *Qwen2.5-3B-Instruct (High-Throughput Fallback):* Ultra-compact (~2 GB in 4-bit), ideal for high-throughput edge deployment and fast batch inference.
*   **Decision:** Select `Qwen2.5-7B-Instruct` as the primary reasoning model and `Qwen2.5-3B-Instruct` as the high-throughput fallback. Train low-rank adapters (~50 MB) using QLoRA.
*   **Consequences:** Guarantees high reproducibility, low inference latency, and deployment flexibility across workstation and edge environments.

---

## ADR-004: Multi-Agent Orchestration with LangGraph StateGraph
*   **Context:** System Architecture Pillar 2 requires genuine Agentic AI with tool calling, shared state, conditional routing, and failure handling—not static script functions.
*   **Decision:** Implement the agentic pipeline using **LangGraph** with a strongly typed Pydantic state container (`MaritimeAgentState`).
*   **Key Capabilities:**
    *   *Dynamic Routing:* Conditional edges dynamically branch based on data availability (e.g., routing to an AIS-degraded path if historical pings are unavailable).
    *   *Resilience:* If any tool returns empty or fails, notes are recorded in `state.degradation_notes` and the graph proceeds without crashing.
    *   *Human-in-the-Loop:* Interrupt checkpoints allow analyst verification of high-risk dark vessel alerts before report finalization.
*   **Consequences:** Produces an auditable, deterministic, and modular multi-agent workflow.

---

## ADR-005: Streamlined Pipeline Architecture vs Heavy MLOps Bloat
*   **Context:** The legacy concept proposed Apache Airflow, continuous satellite streaming, Evidently AI drift triggers, and automatic continuous retraining.
*   **Evaluation:** This infrastructure represents immense devops complexity and runtime fragility that detracts from core remote sensing and reasoning capabilities.
*   **Decision:** Eliminate Airflow, Kubernetes, Docker, and autonomous retraining loops. Implement modular, testable Python pipelines with reproducible evaluation metrics.
*   **Consequences:** The codebase remains fast, transparent, highly portable, and instantly testable.

---

## ADR-006: Replacing Binary Dark Vessel Heuristic with Multi-Domain Feature Engineering
*   **Context:** The legacy proposal asserted that "SAR target + no AIS = dark vessel".
*   **Evaluation:** Under international maritime law (SOLAS V/19), vessels under 300 GT (artisanal dhows, wooden fishing boats) are legally exempt from transmitting AIS. Furthermore, satellite AIS reception is prone to radio packet collisions in congested chokepoints.
*   **Decision:** Reject the binary rule. Elevate Feature Engineering (Pillar 1) to evaluate multi-factor evidence: estimated vessel length (>50m indicates commercial vessel legally bound by SOLAS), radar cross-section, distance from shore, historical AIS gap patterns, and local receiver density.
*   **Consequences:** Elevates the academic rigor and operational credibility of the system.

---

## ADR-007: Official Streamed Sanctions Feeds over Monolithic Aggregations
*   **Context:** Third-party aggregators like OpenSanctions provide bulk dumps (2.42 GB) containing massive non-maritime entity databases (corporate directors, politicans, PEPs).
*   **Decision:** Ingest directly from the official U.S. OFAC SDN XML archive and UN Security Council Consolidated XML, extracting dedicated vessel records and ownership chains.
*   **Consequences:** Ensures 100% authoritative government provenance, zero irrelevant entity memory overhead, and instant sub-millisecond in-memory hash indexing (< 1 ms lookup).
