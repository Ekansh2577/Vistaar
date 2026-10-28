# VISTAAR Evaluation Audit Report (Phase 1 Remediation v2)

**Date:** October 26, 2026  
**Auditor:** Antigravity Evaluation Subsystem  
**Scope:** `evaluation/results/audit_v2/`  
**Evaluation Script:** `evaluation/evaluate_ragas_corrected.py`  
**Input Data:** `evaluation/results/eval_dataset_collected.json` (Existing, unmutated pipeline data)

---

## 1. Executive Summary: What Changed & Current Status

In Phase 1 of the audit, all methodological distortions, silent API defaults, and statistical inaccuracies identified in `audit_report.md` were resolved without modifying your backend, frontend, benchmark questions, or original results.

### Key Changes Implemented:
1. **Zero Silent Fallback Defaults:**
   - Evaluator no longer returns `1.0000` or `0.0000` when an LLM API call fails or times out.
   - All API calls use bounded exponential backoff across model pools (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`).
   - If retries fail, the metric is marked as `FAILED` and recorded separately in `failures_and_refusals.json`.
   - In this run, **0 API calls failed** (`total_failures = 0`); all transient network and rate-limit spikes were absorbed.
2. **Proper Mixed-Answer Verification (Q15):**
   - The evaluator now parses answers containing both factual statements and refusal notes.
   - In **Q15** (*"The FAISS index uses exact Euclidean distance. I could not find this in the document."*), the factual claim was extracted, checked against the retrieved chunk, and verified as supported ($F = 1.0000, 1/1\text{ claims}$).
3. **Transparent Refusal Policy (Separation of Claims vs. Boundary Adherence):**
   - The 13 pure refusal responses are now explicitly flagged (`is_pure_refusal = True`).
   - Instead of artificially inflating Faithfulness by giving $0/0$ claims a score of $1.0$, we report:
     - `faithfulness_factual`: Calculated **only on queries asserting factual claims** ($N=12$).
     - `faithfulness_policy`: Reports adherence to the negative boundary constraint ($N=25$).
4. **Realistic Context Recall (Exclusion of Negative Controls):**
   - The 7 queries with negative reference answers (Q09, Q20–Q25) have no ground-truth facts to retrieve. They are now flagged as `is_negative_control = True` and excluded from factual recall.
   - For the 18 factual/partial queries, Context Recall is **0.9444** (uncovering genuine retrieval gaps on Q14 and Q17, which scored **0.5000**).
5. **Correction of Q01 Context Precision:**
   - In the initial run, Q01 was assigned `0.0000` due to a network connection drop during the evaluation call. With bounded retries, Q01 correctly evaluated Chunk 2 as a hit and scored **0.5000**.
6. **Academic Sample Statistics ($N-1$):**
   - All standard deviations now use Bessel's correction ($N-1$), and every row explicitly reports the valid sample size ($N_{\text{valid}}$).

---

## 2. Quantitative Comparison: Original Audit v1 vs. Corrected v2

| Metric / Dimension | Original Audit v1 (Distorted) | Corrected Audit v2 (Methodologically Sound) | Impact & Rationale |
| :--- | :---: | :---: | :--- |
| **Faithfulness (Factual Claims)** | 1.0000 ($N=25$) | **1.0000 ($N=12$)** | Pure refusals ($N=13$) excluded from $0/0$ division. Factual answers have 100% grounded claims. |
| **Faithfulness (Policy Adherence)** | 1.0000 ($N=25$) | **1.0000 ($N=25$)** | Reports strict adherence to negative boundary constraints. |
| **Context Recall (Factual)** | 1.0000 ($N=25$) | **0.9444 ($N=18$)** | Negative controls excluded. Q14 and Q17 accurately reflect that only 50% of reference facts were in context. |
| **Context Precision** | 0.9000 ($N=25$) | **0.9600 ($N=25$)** | Q01 corrected from `0.0000` (network drop) to `0.5000` (valid hit). |
| **Answer Relevancy (Factual Subset)** | *Not reported separately* | **0.7204 ($N=12$)** | Proves VISTAAR generates highly relevant answers when evidence is present ($\sigma = 0.1163$). |
| **Answer Relevancy (Refusal Subset)** | *Not reported separately* | **0.1502 ($N=13$)** | Formally documents that generic refusals receive low reverse-question cosine similarity. |
| **Answer Relevancy (Overall)** | 0.4239 ($\sigma = 0.2978$, $N$) | **0.4239 ($\sigma = 0.3039$, $N-1$)** | Converted to sample standard deviation. |
| **Total Evaluation Failures** | 2 silent failures (Q01, Q05) | **0 failures** (Full recovery via retries) | Zero silent fallback defaults. |

---

## 3. Breakdown by Evidence Category (Audit v2)

All numbers are derived directly from `evaluation/results/audit_v2/aggregate_metrics_v2.csv`:

### Sufficient Evidence ($N=12$)
- **Faithfulness (Factual):** Mean = **1.0000**, Sample Std = **0.0000** ($N=11$ factual answers; Q09 was a query asking for the refusal string).
- **Answer Relevancy:** Mean = **0.6796**, Sample Std = **0.1850** ($N=12$, peaking at $0.9102$).
- **Context Precision:** Mean = **0.9167**, Sample Std = **0.1946** ($N=12$).
- **Context Recall (Factual):** Mean = **1.0000**, Sample Std = **0.0000** ($N=11$).

### Partial Evidence ($N=7$)
- **Faithfulness (Factual):** Mean = **1.0000** ($N=1$; Q15 asserted a factual claim alongside a refusal).
- **Answer Relevancy:** Mean = **0.2556**, Sample Std = **0.2086** ($N=7$).
- **Context Precision:** Mean = **1.0000**, Sample Std = **0.0000** ($N=7$).
- **Context Recall (Factual):** Mean = **0.8571**, Sample Std = **0.2440** ($N=7$; Q14 and Q17 scored 0.5000).

### Insufficient Evidence ($N=6$)
- **Faithfulness (Factual):** $N=0$ (All 6 are pure refusals).
- **Faithfulness (Policy):** Mean = **1.0000** ($N=6$; 100% negative constraint compliance).
- **Answer Relevancy:** Mean = **0.1090**, Sample Std = **0.0189** ($N=6$).
- **Context Precision (Negative Control):** Mean = **1.0000** ($N=6$; 0 false positive chunks).
- **Context Recall (Factual):** $N=0$ (Negative control; zero facts expected).

---

## 4. Evaluation Implementation Notice (IEEE Transparency)

- **Implementation Category:** Standalone Algorithmic Implementation (RAGAS-compatible).
- **Rationale:** Built directly using Google GenAI and `sentence-transformers` to prevent pip dependency backtracking conflicts in the primary environment.
- **Mathematical Alignment:** Faithfulness, Answer Relevancy, Context Precision ($CP@K$), and Context Recall use the exact mathematical formulations defined in the seminal paper (*Es et al., EMNLP 2023*).
- **Reporting Guidance for Paper:** When writing the paper, state:
  > *"Evaluation was conducted using a standalone algorithmic implementation adhering strictly to the formal mathematical definitions of the RAGAS framework (Es et al., 2023), employing Gemini Flash as the LLM judge and all-MiniLM-L6-v2 for semantic cosine similarities."*

---

## 5. Artifact Index (Audit v2)

All corrected files are located in `evaluation/results/audit_v2/`:
1. **Per-Question Corrected Metrics:**  
   [`per_question_metrics_v2.csv`](file:///c:/Users/ekans/.gemini/antigravity-ide/scratch/vistaar/evaluation/results/audit_v2/per_question_metrics_v2.csv)
2. **Aggregate Statistics (with Sample Std & $N_{\text{valid}}$):**  
   [`aggregate_metrics_v2.csv`](file:///c:/Users/ekans/.gemini/antigravity-ide/scratch/vistaar/evaluation/results/audit_v2/aggregate_metrics_v2.csv)
3. **Failures and Refusals Audit Log:**  
   [`failures_and_refusals.json`](file:///c:/Users/ekans/.gemini/antigravity-ide/scratch/vistaar/evaluation/results/audit_v2/failures_and_refusals.json)
4. **Corrected Evaluator Script:**  
   [`evaluation/evaluate_ragas_corrected.py`](file:///c:/Users/ekans/.gemini/antigravity-ide/scratch/vistaar/evaluation/evaluate_ragas_corrected.py)
