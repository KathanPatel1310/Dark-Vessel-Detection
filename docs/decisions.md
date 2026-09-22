# Architectural Decision Records (ADRs)

## ADR-001: Replacement of SciHub / sentinelsat with CDSE & GFW SAR APIs
*   **Context:** The legacy document specified `sentinelsat` connecting to `scihub.copernicus.eu`. ESA permanently closed SciHub on October 31, 2023. Scripts relying on `sentinelsat` fail immediately.
*   **Decision:** Migrate SAR data access to the new Copernicus Data Space Ecosystem (CDSE) APIs (STAC/OData) and utilize the Global Fishing Watch 4Wings SAR presence dataset (`public-global-sar-presence:latest`).
*   **Consequences:** Ensures full programmatic viability without broken legacy dependencies. Allows querying pre-correlated SAR-AIS detections on-demand, saving hundreds of gigabytes in local storage.

---

## ADR-002: Decoupled Detection-Reasoning Architecture vs Two-Stage VLM (LLaVA)
*   **Context:** The original PDF proposed fine-tuning LLaVA-1.6 (or InternVL2) in two stages: Stage 1 to detect ships from SAR chips, and Stage 2 to generate textual reports.
*   **Evaluation:**
    1.  Natural image VLMs are poorly suited for radar microwave backscatter matrices.
    2.  VLM vision encoders require massive GPU VRAM (>24 GB) to fine-tune.
    3.  Asking a vision model to generate tabular and legal text leads to hallucinations and inefficiency.
*   **Decision:** Decouple computer vision from intelligence reasoning. Use specialized radar feature extractors / lightweight detectors (e.g. YOLOv8 on SSDD/HRSID or pre-extracted morphological features) to generate structured numerical metrics (length, width, RCS, backscatter ratio), then pass these clean features to an LLM specialized in text reasoning.
*   **Consequences:** Drastically lowers compute requirements, enables running on student-accessible hardware (or Colab), and focuses LLM fine-tuning entirely on the professor's core requirement: maritime intelligence synthesis.

---

## ADR-003: Selection of Qwen 2.5 (7B / 3B) for QLoRA Fine-Tuning
*   **Context:** The professor's 3rd pillar mandates supervised fine-tuning of an open-weight LLM on domain data.
*   **Comparison:**
    *   *LLaVA-1.6:* Architecturally inappropriate for structured textual synthesis.
    *   *Llama-3.1-8B:* Strong, but requires gated licensing tokens and ~16 GB storage.
    *   *Mistral-7B-v0.3:* Good, but higher memory footprint during 4-bit SFT.
    *   *Qwen2.5-7B-Instruct (Primary):* Apache 2.0 license, state-of-the-art reasoning, exceptional JSON structure compliance, fits in ~4.5 GB in 4-bit.
    *   *Qwen2.5-3B-Instruct (Fallback):* Ultra-compact (~2 GB storage in 4-bit), runs on virtually any laptop or free Colab instance.
*   **Decision:** Select `Qwen2.5-7B-Instruct` as primary model and `Qwen2.5-3B-Instruct` as ultra-low-storage fallback. Train low-rank adapters (~50 MB) using QLoRA.
*   **Consequences:** Guarantees reproducibility on standard student machines without costly cloud infrastructure.

---

## ADR-004: Multi-Agent Orchestration with LangGraph StateGraph
*   **Context:** The professor's 2nd pillar requires genuine Agentic AI with tool calling, shared state, conditional routing, and failure handling—not static script functions.
*   **Decision:** Implement the agentic pipeline using **LangGraph** with a strongly typed Pydantic state container (`MaritimeAgentState`).
*   **Key Capabilities:**
    *   *Dynamic Routing:* Conditional edges dynamically branch based on data availability (e.g., routing to an AIS-degraded path if historical pings are unavailable).
    *   *Resilience:* If any tool returns empty or fails, notes are recorded in `state.degradation_notes` and the graph proceeds.
    *   *Human-in-the-Loop:* Interrupt checkpoints allow analyst verification of high-risk dark vessel alerts before report generation.
*   **Consequences:** Produces a traceable, academic-grade multi-agent system.

---

## ADR-005: Removal of Heavy MLOps (Airflow, Kubernetes, Evidently Retraining)
*   **Context:** The PDF proposed Apache Airflow, continuous satellite streaming, Evidently AI drift triggers, and automatic continuous retraining.
*   **Evaluation:** This infrastructure represents immense devops complexity, consumes tens of gigabytes of disk space, and is entirely orthogonal to an academic data science project.
*   **Decision:** Eliminate Airflow, Kubernetes, Docker, and autonomous retraining loops. Implement modular, testable Python scripts with reproducible offline evaluation metrics.
*   **Consequences:** The codebase remains fast, transparent, and completely runnable on a standard developer machine.

---

## ADR-006: Replacing Binary Dark Vessel Heuristic with Multi-Domain Feature Engineering
*   **Context:** The PDF asserted that "SAR target + no AIS = dark vessel".
*   **Evaluation:** Under international maritime law (SOLAS V/19), vessels under 300 GT (artisanal dhows, wooden fishing boats) are legally exempt from transmitting AIS. Furthermore, satellite AIS reception is prone to radio packet collisions in congested chokepoints.
*   **Decision:** Reject the binary rule. Elevate Feature Engineering (Pillar 1) to evaluate multi-factor evidence: estimated vessel length (>50m indicates commercial vessel legally bound by SOLAS), radar cross-section, distance from shore, historical AIS gap patterns, and local receiver density.
*   **Consequences:** Elevates the academic rigor and operational credibility of the project.

---

## ADR-007: Official Compressed Sanctions Data over Monolithic Dumps
*   **Context:** OpenSanctions provides a comprehensive database, but its full dump is **2.42 GB**.
*   **Decision:** Enforce the user's strict local storage constraint by downloading the official U.S. OFAC SDN compressed XML archive (**~15 MB**) and UN Security Council Consolidated XML (**~2 MB**), and extracting only maritime vessel entities.
*   **Consequences:** Saves >2.4 GB of disk space while using 100% official, authoritative government sources.
