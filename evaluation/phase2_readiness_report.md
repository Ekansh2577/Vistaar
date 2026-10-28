# VISTAAR Phase 2 Pre-Experiment Readiness & Audit Report

**Audit Date:** 2026-10-26  
**Evaluation Target:** VISTAAR RAG Retrieval & Generation Top-$k$ Ablation Suite ($k \in \{3, 5, 8\}$)  
**Readiness Status:** **READY FOR EXPERIMENTATION** (Pending user review approval)

---

## 1. Executive Summary
All prerequisite assets, dataset splits, corpus documents, integrity hashes, and runner harnesses for Phase 2 research evaluation have been constructed and verified. All work is strictly isolated in `evaluation/`. No backend, frontend, or existing Phase 1 evaluation outputs were modified or overwritten.

---

## 2. Review Checklist & Architectural Verification

### 2.1 Adversarial Queries (PH2-Q30 to PH2-Q32)
- **Status:** **RETAINED & VERIFIED**
- **Configuration:** Questions PH2-Q30, PH2-Q31, and PH2-Q32 deliberately present deceptive keyword intersections with `doc_05_acoustic_distractor.txt` (e.g., Kalman filtering, NLMS adaptive echo cancellation, Butterworth filtering) framed in the context of text chunk indexing.
- **Expected Ground Truth:** Complete refusal. The reference answers affirm that while these signal processing techniques are described in the corpus, they are not applied to text chunk vectors or embeddings.

### 2.2 Partial-Answer Queries (PH2-Q21 to PH2-Q26)
- **Status:** **VERIFIED & CALIBRATED**
- **Configuration:** Each question couples an explicitly supported factual query with an absent query (e.g., chunk size vs. sentence length threshold; vector dimension vs. pre-training learning rate).
- **Refusal Policy:** The ground-truth annotations explicitly decouple the factual component from the refusal component (`partial_scope: {"supported": "...", "unsupported": "..."}`).
- **Evaluation Rule:** Evaluator models will verify that the factual answer is accurate and that the unsupported component is acknowledged as absent, without penalizing lexical variation or requiring an exact canned refusal sentence.

### 2.3 Cross-Document Coupling in PH2-Q16
- **Status:** **GENUINELY MULTI-DOCUMENT (DOC-01 + DOC-02 REQUIRED)**
- **Question:** *"How are tabular structures extracted from documents in VISTAAR, and what chunking parameters are subsequently applied to the extracted Markdown tables?"*
- **Evidence Verification:**
  - **DOC-02 (Multimodal Ingestion):** Contains the table detection mechanism (horizontal $1 \times 40$ and vertical $40 \times 1$ morphological kernels) and Markdown table extraction syntax. It does *not* state chunking window or overlap parameters.
  - **DOC-01 (Architecture):** Contains the sliding-window chunking parameters (window size 1000 characters, overlap 200 characters, stride 800 characters). It does *not* explain table extraction kernels.
  - **Conclusion:** Answering both clauses of PH2-Q16 strictly requires retrieving and synthesizing context chunks from both documents.

### 2.4 Synthetic Corpus Disclaimers & Real-World Demarcation
- **Status:** **STRICTLY LABELED**
- **Notice Embedded:** All 5 documents in `evaluation/corpus/` carry the header:
  `[SYNTHETIC EVALUATION CORPUS - CONTROLLED BENCHMARK DATASET FOR VISTAAR RAG RESEARCH EVALUATION. NOT AN EMPIRICAL HARDWARE/SYSTEM SPECIFICATION.]`
- **Scientific Guardrail:** The benchmark text numbers (such as Xeon CPU latency, A10G throughput, Conformer-CTC 10,000 hours, Tesseract 72% gate) are synthetic controlled reference artifacts engineered to evaluate retrieval selectivity and fact-checking. They must **not** be presented as empirical claims regarding the user's real hardware or production deployment.

### 2.5 Experiment Runner Index Reset & Top-$k$ Parameterization
- **Status:** **VERIFIED**
- In `evaluation/runners/run_phase2_experiments.py`:
  - `initialize_phase2_index` cleanly executes `index.reset()` and `stored_chunks.clear()`, reloading the 5 corpus documents (62 chunks total).
  - Condition loops correctly pass `k=3`, `k=5`, and `k=8` directly to `vector_store.search(q_emb, k=k)`.

### 2.6 Frozen Test Suite & Latency Measurement Isolation
- **Status:** **VERIFIED**
- **Test Integrity:** The identical 24 frozen test questions from `test_queries_frozen.json` are evaluated across all three conditions ($k=3, 5, 8$).
- **Latency Isolation:** Retrieval latency (`retrieval_latency_ms`) and LLM generation latency (`generation_latency_ms`) are recorded independently via high-resolution monotonic timers (`time.perf_counter()`).
- **Failure Preservation:** API exceptions or empty responses are caught and preserved with `is_api_failure: True` and the full exception string, preventing silent crashes or false score assignment.

### 2.7 Token Measurement & Cost Accounting
- **Status:** **EXPLICITLY LABELED AS ESTIMATES**
- **Measurement Method:** Because the existing backend `ask_gemini` implementation returns a raw string (`response.text`), token usage and operational costs are calculated using standard character-length heuristics:
  $$\text{prompt\_tokens\_est} = \lfloor \text{len(prompt)} / 4 \rfloor, \quad \text{response\_tokens\_est} = \lfloor \text{len(response)} / 4 \rfloor$$
- **Cost Calculation:** Based on Gemini flash-lite tier rates (\$0.075 / 1M input tokens, \$0.300 / 1M output tokens).
- **Labeling:** Explicitly marked in all CSV and JSON output records under `token_measurement_type: "heuristic_estimate_4_chars_per_token"`.

### 2.8 Review Transparency
- **Notice on Verification:** Automated programmatic verification (SHA-256 integrity, exact chunk bounds, disjointness, and span mapping) passed with 100% compliance. **No claim of independent manual review is made**; human inspection should be completed by the researcher as documented in Section 3.

---

## 3. Human Review Items for Researcher Approval

Before executing `python evaluation/runners/run_phase2_experiments.py`, please confirm:
1. **Adversarial Distractors:** You approve the inclusion of PH2-Q30, PH2-Q31, and PH2-Q32 as zero-evidence distractor queries where complete refusal is expected.
2. **Partial Evidence Formulation:** You approve the two-stage grading policy for PH2-Q21 through PH2-Q26 (evaluating factual grounding on the supported clause and refusal on the unsupported clause).
3. **Execution Approval:** You are ready to trigger the real Gemini API generation runs for the 24 frozen test queries across $k \in \{3, 5, 8\}$.

---

## 4. Final Verdict
**The Phase 2 benchmark harness is fully prepared, mathematically validated, and ready for execution upon user signal.**
