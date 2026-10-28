# VISTAAR RAGAS Evaluation Audit Report

**Date:** October 26, 2026  
**Auditor:** Antigravity Evaluation Subsystem  
**Scope:** `evaluation/results/per_question_metrics.csv`, `evaluation/results/aggregate_metrics.csv`, `evaluation/results/eval_dataset_collected.json`, `evaluation/evaluate_ragas_standalone.py`, and `evaluation/collect_eval_data.py`.  
**Status:** Completed. No backend, frontend, or existing result files modified.

---

## 1. Executive Summary: Are the Current Results Trustworthy?

**Verdict: Partially Trustworthy / Not Yet Ready for Research Publication.**

While the data collection pipeline (`collect_eval_data.py`) successfully captured authentic responses and contexts from the VISTAAR pipeline without fabrication, the evaluated metrics contain **significant methodological distortions, silent API fallback defaults, and structural artifacts**:

1. **Faithfulness ($\mu = 1.0000, \sigma = 0.0000$) is artificially inflated:** 
   - 14 of the 25 questions bypassed claim extraction via hardcoded refusal shortcuts.
   - At least one question (Q05) suffered a network timeout (`[Errno 11001] getaddrinfo failed`), which silently triggered a fallback heuristic that awarded a perfect `1.0000`.
2. **Context Recall ($\mu = 1.0000, \sigma = 0.0000$) is trivially saturated:** 
   - The corpus evaluated (`test_sample.txt`) is only 1,367 characters long and produces only **2 chunks**.
   - With $k=8$, FAISS retrieved 100% of the entire knowledge base for every single query, making high recall trivial.
3. **Answer Relevancy ($\mu = 0.4239$) is heavily penalized by negative refusals:**
   - For queries with insufficient evidence (Q20–Q25), VISTAAR correctly returned `"I could not find this in the document."`
   - Reverse-question generation for refusals generates questions like *"What could not be found?"*, which has near-zero cosine similarity with topical questions like *"What is the monthly pricing tier...?"* This drags the score down to $0.1090$, giving the false impression that VISTAAR produces irrelevant answers.
4. **Context Precision on Q01 was distorted by a network error:**
   - Q01 recorded a score of `0.0000` despite retrieving relevant text (Chunk 2 contained the exact chunk size). The log proves that 15 consecutive network connection drops caused the evaluator to receive an empty response, which defaulted to `0.0000`.
5. **Statistical Convention:**
   - Standard deviations in `aggregate_metrics.csv` divide by $N$ (population variance) instead of $N-1$ (sample variance with Bessel's correction), which is standard in academic benchmarks.

---

## 2. In-Depth Audit Findings

### Finding 1: Silent Fallback Defaults on API Failures
In `evaluation/evaluate_ragas_standalone.py`, lines 157–159 and lines 319–320:
```python
claims = data.get("claims", [])
if not claims:
    # Fallback heuristic if decomposition returned empty
    return {"score": 1.0, "total_claims": 0, "supported_claims": 0, "reason": "No factual claims extracted."}
```
- **The Issue:** When an API call crashes due to network interruption (`WinError 10054` or `Errno 11001`) or rate limiting (`429`), `call_gemini_judge()` returns `""`. `clean_json_response()` produces `{}`. The evaluator then silently falls back to `1.0`.
- **Evidence in Log (`task-1241.log`):**
  - **Q05 Faithfulness:** Failed with 15 connection errors; logged `-> Faithfulness: 1.0000 (0/0 claims supported)`.
  - **Q01 Context Precision:** In `evaluate_context_precision`, empty output resulted in `chunk_relevances = [0, 0]`, recording `0.0000` instead of retrying or failing gracefully.

### Finding 2: Trivially Saturated Retrieval Corpus (Only 2 Chunks)
In `evaluation/collect_eval_data.py`:
```python
corpus = WORKSPACE_DIR / "test_sample.txt" # 1,367 characters
chunks = chunk_text(text, size=1000, overlap=200) # Output: exactly 2 chunks
```
- **The Issue:** The entire FAISS index contains only **2 chunks**.
- **Impact on Context Recall:** When $k=8$, FAISS returns all available chunks (2 chunks). Every question receives the complete document in its prompt. Context Recall is guaranteed to be 1.0 regardless of retrieval quality.
- **Reviewer Vulnerability:** Academic reviewers will immediately reject a claim of "100% Context Recall across an enterprise RAG system" if the test corpus only contains 2 text chunks.

### Finding 3: Metric Incompatibility with Negative Refusals
In `evaluation/evaluate_ragas_standalone.py`:
- Answer Relevancy measures the cosine similarity between the original query $q$ and $n=3$ generated questions $q_i$ answering the model's response.
- When VISTAAR properly adheres to negative boundaries and responds with `"I could not find this in the document."`, the generated reverse questions are generic meta-questions (*"Was the document searched?"*).
- Cosine similarity between $q$ and $q_i$ drops to $0.07 - 0.15$.
- **Result:** VISTAAR is penalized for strictly avoiding hallucinations. The average Answer Relevancy for insufficient-evidence questions is **0.1090**, pulling the overall system average down from **0.6796** to **0.4239**.

### Finding 4: Inexact Treatment of Refusal Strings in Responses
In `evaluation/evaluate_ragas_standalone.py`:
```python
refusal_patterns = ["could not find this in the document", ...]
if any(p in response.lower() for p in refusal_patterns):
    return {"score": 1.0, ...}
```
- For **Q15**, VISTAAR generated:
  `"The FAISS index uses exact Euclidean distance. I could not find this in the document."`
- Because the string contained `"could not find this in the document"`, the evaluator classified the entire answer as a refusal, skipping claim extraction on `"The FAISS index uses exact Euclidean distance."`

### Finding 5: Calculation of Averages and Standard Deviations
- **Arithmetic vs. Harmonic Mean:** The "Overall RAGAS Score" is calculated as a simple unweighted arithmetic mean:
  $$\text{Composite} = \frac{\text{Faithfulness} + \text{Answer Relevancy} + \text{Context Precision} + \text{Context Recall}}{4}$$
  While mathematically valid, standard RAG literature generally reports retrieval ($CP, CR$) and generation ($F, AR$) metrics separately rather than conflating them into a single unweighted average.
- **Standard Deviation Formula:** `compute_stats` uses `variance = sum(...) / len(values)`, which is population variance $\sigma = \sqrt{\frac{1}{N}\sum(x_i - \mu)^2}$. For small empirical samples ($N=25$, or $N=6$ in subgroups), the unbiased sample standard deviation with Bessel's correction $s = \sqrt{\frac{1}{N-1}\sum(x_i - \bar{x})^2}$ should be reported.

---

## 3. Question-by-Question Audit Summary

| Question ID | Category | Reported Status | Audit Finding |
| :--- | :--- | :---: | :--- |
| **Q01** | Sufficient | $CP = 0.0000$ | **Distorted by network drop.** Chunk 2 has the exact answer. Score should be $\approx 0.5000$. |
| **Q02** | Sufficient | All valid | Real calculation. Valid. |
| **Q03** | Sufficient | All valid | Real calculation. Valid. |
| **Q04** | Sufficient | All valid | Real calculation. Valid. |
| **Q05** | Sufficient | $F = 1.0000 (0/0)$ | **Distorted by network timeout.** Silently defaulted to 1.0 without extracting claims. |
| **Q06–Q08** | Sufficient | All valid | Real calculation. Valid. |
| **Q09** | Sufficient | $AR = 0.2227$ | Negative refusal penalty on an answerable query about refusal strings. |
| **Q10–Q12** | Sufficient | All valid | Real calculation. Handled API retries successfully. |
| **Q13–Q14** | Partial | $F = 1.0000 (0/0)$ | Refusal shortcut triggered because model responded with refusal string. |
| **Q15** | Partial | $F = 1.0000 (0/0)$ | Partial answer (`Euclidean distance`) bypassed claim verification due to refusal substring. |
| **Q16** | Partial | $F = 1.0000 (0/0)$ | Refusal shortcut triggered. |
| **Q17** | Partial | $CP = 0.0000$ | Undefined precision case (no relevant chunks existed for pre-upload error details). |
| **Q18–Q19** | Partial | $F = 1.0000 (0/0)$ | Refusal shortcut triggered. |
| **Q20–Q25** | Insufficient | $AR \approx 0.10$ | Valid negative refusals heavily penalized by standard Answer Relevancy formula. |

---

## 4. What Needs Fixing First (Prioritized Action Plan)

Before running new experiments or submitting results to an IEEE paper:

1. **Fix API Failure Handling (Remove Silent 1.0 Defaults):**
   - If an LLM call fails after retries, the script must throw an error, mark the question as `FAILED`, or retry with backoff—never silently return `1.0000` or `0.0000`.
2. **Expand the Corpus Document (Realistic Retrieval Scale):**
   - Ingest a multi-page document or realistic technical manual of at least 50–100 chunks ($\ge 50,000$ characters) so that FAISS $k=8$ retrieval is tested against genuine distractors and negative chunks.
3. **Separate Reporting of Answerable vs. Refusal Queries:**
   - In your IEEE paper, report Answer Relevancy separately for **Sufficient-Evidence** queries ($\mu = 0.6796$) vs. **Insufficient-Evidence** queries ($\mu = 0.1090$), explaining that RAGAS Answer Relevancy is mathematically ill-suited for correct negative refusals.
4. **Fix Mixed Answer Parsing in Refusal Checks:**
   - Update `evaluate_faithfulness` so that if an answer contains factual claims alongside a refusal (like Q15), the factual claims are still extracted and verified.
5. **Adopt Sample Standard Deviation ($N-1$):**
   - Update `compute_stats` to use `math.sqrt(sum(...) / (len(values) - 1))` to align with academic publishing standards.
