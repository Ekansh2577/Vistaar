# VISTAAR Research Evaluation — Phase 2 Top-k Ablation Results

**Evaluation Split:** Frozen Test Suite (24 Questions across 5 Documents / 62 Chunks)
**Configurations Evaluated:** $k \in \{3, 5, 8\}$

## 1. Comparative Performance Matrix

| Metric | Condition $k=3$ | Condition $k=5$ | Condition $k=8$ |
| :--- | :---: | :---: | :---: |
| **Valid Evaluations (N)** | 24/24 | 24/24 | 24/24 |
| **Retrieval Hit Rate @ k** | 1.0000 | 1.0000 | 1.0000 |
| **Retrieval Precision @ k** | 0.4333 | 0.3300 | 0.2250 |
| **Retrieval Recall @ k** | 0.7625 | 0.9167 | 0.9708 |
| **Single-Doc Recall @ k** | 0.9000 | 1.0000 | 1.0000 |
| **Multi-Doc Recall @ k** | 0.5417 | 0.8056 | 0.9028 |
| **Mean Reciprocal Rank (MRR)** | 0.9500 | 0.9500 | 0.9500 |
| **Semantic Answer Similarity** | 0.8475 | 0.8491 | 0.8560 |
| **Refusal Accuracy (Insufficient)** | 1.0000 | 1.0000 | 1.0000 |
| **Partial-Answer Accuracy** | 0.7500 | 0.7500 | 0.7500 |
| **Mean Retrieval Latency (ms)** | 21.51 ms | 16.99 ms | 18.13 ms |
| **Mean Generation Latency (ms)** | 6132.20 ms | 3620.46 ms | 4966.70 ms |
| **Mean Prompt Tokens (Est.)** | 788.1 | 1291.7 | 2028.8 |
| **Total Condition Cost (Est. USD)** | $0.00176 | $0.00267 | $0.00400 |

*Note: Token counts and costs are heuristic estimates (approx. 4 characters per token). Retrieval metrics are computed strictly on ground-truth chunk intersections independently of LLM generation.*
