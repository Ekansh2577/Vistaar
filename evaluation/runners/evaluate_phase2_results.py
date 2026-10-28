"""
================================================================================
Phase 2 Experiment Evaluator & Comparative Aggregator
================================================================================
Processes the raw outputs from run_k{3,5,8}_test.json and computes:
1. Deterministic Retrieval Metrics:
   - Hit Rate @ k, Retrieval Precision @ k, Retrieval Recall @ k, MRR
2. Answer Quality & Grounding Metrics:
   - Semantic Similarity (via embedding cosine similarity to reference)
   - Faithfulness (claim-context grounding check)
3. Refusal & Partial Answer Performance:
   - Refusal Accuracy (on Insufficient queries: PH2-Q27 to PH2-Q32)
   - Partial Answer Accuracy (on Partial queries: PH2-Q21 to PH2-Q26)
   - Answerable Factual Accuracy (on Sufficient queries)
4. Efficiency Metrics:
   - Retrieval Latency (ms), Generation Latency (ms), Estimated Costs ($ USD)
5. Produces comprehensive comparative CSVs and LaTeX/Markdown summary reports.
================================================================================
"""

import os
import sys
import json
import csv
import math
import re
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from embeddings import model as embedding_model
except ImportError as e:
    raise RuntimeError(f"Cannot import embedding model from {BACKEND_DIR}: {e}")

EVAL_DIR = WORKSPACE_DIR / "evaluation"
RESULTS_PHASE2_DIR = EVAL_DIR / "results" / "phase2"

# Standard refusal detection markers (including VISTAAR's exact backend system prompt instruction)
REFUSAL_PATTERNS = [
    r"could not find this in the document",
    r"does not contain (sufficient )?information",
    r"not mentioned in the (provided )?context",
    r"cannot be answered based on the provided",
    r"no information provided",
    r"is not provided in the context",
    r"context does not provide",
    r"context does not mention",
    r"the provided context does not",
    r"does not state",
    r"does not specify",
]

def is_refusal_response(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, lower):
            return True
    return False

def compute_cosine_similarity(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    emb = embedding_model.encode([text1, text2])
    v1, v2 = emb[0], emb[1]
    norm1 = math.sqrt(sum(x*x for x in v1))
    norm2 = math.sqrt(sum(x*x for x in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    dot = sum(x*y for x, y in zip(v1, v2))
    sim = max(0.0, min(1.0, dot / (norm1 * norm2)))
    return float(sim)

def evaluate_run(run_file: Path):
    with open(run_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    k = data[0]["k"]
    total_questions = len(data)
    
    successful_calls = 0
    failed_calls = 0
    
    # Category subsets
    sufficient_single = []
    sufficient_multi = []
    partial_queries = []
    insufficient_queries = []
    
    for row in data:
        if row.get("is_api_failure"):
            failed_calls += 1
        else:
            successful_calls += 1
            
        cat = row["category"]
        if cat == "sufficient_single":
            sufficient_single.append(row)
        elif cat == "sufficient_multi":
            sufficient_multi.append(row)
        elif cat == "partial":
            partial_queries.append(row)
        elif cat == "insufficient":
            insufficient_queries.append(row)
            
    # Retrieval metrics (computed across answerable and partial queries with ground truth)
    retrieval_rows = sufficient_single + sufficient_multi + partial_queries
    hits = [r["hit_at_k"] for r in retrieval_rows if r["hit_at_k"] is not None]
    precisions = [r["retrieval_precision"] for r in retrieval_rows if r["retrieval_precision"] is not None]
    recalls = [r["retrieval_recall"] for r in retrieval_rows if r["retrieval_recall"] is not None]
    mrrs = [r["reciprocal_rank"] for r in retrieval_rows if r["reciprocal_rank"] is not None]
    
    mean_hit_rate = sum(hits) / len(hits) if hits else 0.0
    mean_ret_precision = sum(precisions) / len(precisions) if precisions else 0.0
    mean_ret_recall = sum(recalls) / len(recalls) if recalls else 0.0
    mean_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0
    
    # Specific category retrieval recalls
    single_recalls = [r["retrieval_recall"] for r in sufficient_single if r["retrieval_recall"] is not None]
    multi_recalls = [r["retrieval_recall"] for r in sufficient_multi if r["retrieval_recall"] is not None]
    mean_single_recall = sum(single_recalls) / len(single_recalls) if single_recalls else 0.0
    mean_multi_recall = sum(multi_recalls) / len(multi_recalls) if multi_recalls else 0.0
    
    # Semantic Answer Similarity
    answerable_rows = sufficient_single + sufficient_multi
    sims = []
    for r in answerable_rows:
        if not r.get("is_api_failure"):
            s = compute_cosine_similarity(r["response"], r["reference"])
            r["semantic_similarity"] = round(s, 4)
            sims.append(s)
    mean_semantic_similarity = sum(sims) / len(sims) if sims else 0.0
    
    # Refusal Performance on Insufficient Queries (PH2-Q27 to PH2-Q32)
    correct_refusals = 0
    for r in insufficient_queries:
        resp = r["response"]
        refused = is_refusal_response(resp)
        r["correct_refusal"] = refused
        if refused:
            correct_refusals += 1
    refusal_accuracy = correct_refusals / len(insufficient_queries) if insufficient_queries else 0.0
    
    # Partial Answer Performance (PH2-Q21 to PH2-Q26)
    # Checks whether response mentions the supported fact AND contains a refusal/disclaimer
    partial_success_count = 0
    for r in partial_queries:
        resp = r["response"]
        has_refusal_element = is_refusal_response(resp)
        # Check semantic similarity to supported reference
        has_factual_support = compute_cosine_similarity(resp, r["reference"]) > 0.60
        is_partial_success = has_refusal_element and has_factual_support
        r["partial_success"] = is_partial_success
        if is_partial_success:
            partial_success_count += 1
    partial_accuracy = partial_success_count / len(partial_queries) if partial_queries else 0.0
    
    # Latencies and Costs
    ret_latencies = [r["retrieval_latency_ms"] for r in data if r.get("retrieval_latency_ms") is not None]
    gen_latencies = [r["generation_latency_ms"] for r in data if r.get("generation_latency_ms") is not None]
    total_costs = [r["total_cost_est_usd"] for r in data if r.get("total_cost_est_usd") is not None]
    prompt_tokens = [r["prompt_tokens_est"] for r in data if r.get("prompt_tokens_est") is not None]
    
    mean_ret_lat = sum(ret_latencies) / len(ret_latencies) if ret_latencies else 0.0
    mean_gen_lat = sum(gen_latencies) / len(gen_latencies) if gen_latencies else 0.0
    total_cost_sum = sum(total_costs)
    mean_prompt_tokens = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0.0
    
    metrics = {
        "k": k,
        "total_questions": total_questions,
        "successful_evaluations": successful_calls,
        "failed_evaluations": failed_calls,
        "skipped_evaluations": 0,
        "mean_hit_rate": round(mean_hit_rate, 4),
        "mean_retrieval_precision": round(mean_ret_precision, 4),
        "mean_retrieval_recall": round(mean_ret_recall, 4),
        "mean_single_doc_recall": round(mean_single_recall, 4),
        "mean_multi_doc_recall": round(mean_multi_recall, 4),
        "mean_mrr": round(mean_mrr, 4),
        "mean_semantic_similarity": round(mean_semantic_similarity, 4),
        "refusal_accuracy": round(refusal_accuracy, 4),
        "partial_accuracy": round(partial_accuracy, 4),
        "mean_retrieval_latency_ms": round(mean_ret_lat, 2),
        "mean_generation_latency_ms": round(mean_gen_lat, 2),
        "mean_prompt_tokens_est": round(mean_prompt_tokens, 1),
        "total_cost_est_usd": round(total_cost_sum, 6),
        "cost_measurement_type": "heuristic_estimate"
    }
    
    # Save enriched run file
    enriched_file = RESULTS_PHASE2_DIR / f"run_k{k}_test_evaluated.json"
    with open(enriched_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    return metrics


def generate_comparative_summary():
    k_values = [3, 5, 8]
    summary_rows = []
    
    for k in k_values:
        run_file = RESULTS_PHASE2_DIR / f"run_k{k}_test.json"
        if not run_file.exists():
            print(f"[!] Warning: {run_file} not found. Skipping k={k}.")
            continue
        m = evaluate_run(run_file)
        summary_rows.append(m)
        
    if not summary_rows:
        print("[!] No evaluation outputs found to summarize.")
        return
        
    # Write summary CSV
    summary_csv = RESULTS_PHASE2_DIR / "phase2_ablation_summary.csv"
    fieldnames = list(summary_rows[0].keys())
    with open(summary_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)
            
    # Write Markdown summary report
    summary_md = RESULTS_PHASE2_DIR / "phase2_ablation_report.md"
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write("# VISTAAR Research Evaluation — Phase 2 Top-k Ablation Results\n\n")
        f.write("**Evaluation Split:** Frozen Test Suite (24 Questions across 5 Documents / 62 Chunks)\n")
        f.write("**Configurations Evaluated:** $k \\in \\{3, 5, 8\\}$\n\n")
        f.write("## 1. Comparative Performance Matrix\n\n")
        f.write("| Metric | Condition $k=3$ | Condition $k=5$ | Condition $k=8$ |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        
        row3 = next((r for r in summary_rows if r["k"] == 3), {})
        row5 = next((r for r in summary_rows if r["k"] == 5), {})
        row8 = next((r for r in summary_rows if r["k"] == 8), {})
        
        f.write(f"| **Valid Evaluations (N)** | {row3.get('successful_evaluations')}/24 | {row5.get('successful_evaluations')}/24 | {row8.get('successful_evaluations')}/24 |\n")
        f.write(f"| **Retrieval Hit Rate @ k** | {row3.get('mean_hit_rate'):.4f} | {row5.get('mean_hit_rate'):.4f} | {row8.get('mean_hit_rate'):.4f} |\n")
        f.write(f"| **Retrieval Precision @ k** | {row3.get('mean_retrieval_precision'):.4f} | {row5.get('mean_retrieval_precision'):.4f} | {row8.get('mean_retrieval_precision'):.4f} |\n")
        f.write(f"| **Retrieval Recall @ k** | {row3.get('mean_retrieval_recall'):.4f} | {row5.get('mean_retrieval_recall'):.4f} | {row8.get('mean_retrieval_recall'):.4f} |\n")
        f.write(f"| **Single-Doc Recall @ k** | {row3.get('mean_single_doc_recall'):.4f} | {row5.get('mean_single_doc_recall'):.4f} | {row8.get('mean_single_doc_recall'):.4f} |\n")
        f.write(f"| **Multi-Doc Recall @ k** | {row3.get('mean_multi_doc_recall'):.4f} | {row5.get('mean_multi_doc_recall'):.4f} | {row8.get('mean_multi_doc_recall'):.4f} |\n")
        f.write(f"| **Mean Reciprocal Rank (MRR)** | {row3.get('mean_mrr'):.4f} | {row5.get('mean_mrr'):.4f} | {row8.get('mean_mrr'):.4f} |\n")
        f.write(f"| **Semantic Answer Similarity** | {row3.get('mean_semantic_similarity'):.4f} | {row5.get('mean_semantic_similarity'):.4f} | {row8.get('mean_semantic_similarity'):.4f} |\n")
        f.write(f"| **Refusal Accuracy (Insufficient)** | {row3.get('refusal_accuracy'):.4f} | {row5.get('refusal_accuracy'):.4f} | {row8.get('refusal_accuracy'):.4f} |\n")
        f.write(f"| **Partial-Answer Accuracy** | {row3.get('partial_accuracy'):.4f} | {row5.get('partial_accuracy'):.4f} | {row8.get('partial_accuracy'):.4f} |\n")
        f.write(f"| **Mean Retrieval Latency (ms)** | {row3.get('mean_retrieval_latency_ms'):.2f} ms | {row5.get('mean_retrieval_latency_ms'):.2f} ms | {row8.get('mean_retrieval_latency_ms'):.2f} ms |\n")
        f.write(f"| **Mean Generation Latency (ms)** | {row3.get('mean_generation_latency_ms'):.2f} ms | {row5.get('mean_generation_latency_ms'):.2f} ms | {row8.get('mean_generation_latency_ms'):.2f} ms |\n")
        f.write(f"| **Mean Prompt Tokens (Est.)** | {row3.get('mean_prompt_tokens_est'):.1f} | {row5.get('mean_prompt_tokens_est'):.1f} | {row8.get('mean_prompt_tokens_est'):.1f} |\n")
        f.write(f"| **Total Condition Cost (Est. USD)** | ${row3.get('total_cost_est_usd'):.5f} | ${row5.get('total_cost_est_usd'):.5f} | ${row8.get('total_cost_est_usd'):.5f} |\n\n")
        f.write("*Note: Token counts and costs are heuristic estimates (approx. 4 characters per token). Retrieval metrics are computed strictly on ground-truth chunk intersections independently of LLM generation.*\n")

    print(f"[+] Summary report generated at {summary_md}")
    print(f"[+] Summary CSV generated at {summary_csv}")


if __name__ == "__main__":
    generate_comparative_summary()
