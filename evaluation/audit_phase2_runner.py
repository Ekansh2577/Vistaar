"""
Detailed audit calculation script for Phase 2 results.
"""

import json
from pathlib import Path
import csv

RESULTS_DIR = Path("evaluation/results/phase2")
DATASETS_DIR = Path("evaluation/datasets")

test_queries = json.load(open(DATASETS_DIR / "test_queries_frozen.json", encoding="utf-8"))
gt_by_id = {q["question_id"]: q for q in test_queries}

print(f"Total frozen test questions: {len(test_queries)}")
cats = {}
for q in test_queries:
    cats[q["category"]] = cats.get(q["category"], 0) + 1
print(f"Categories in frozen test: {cats}")

k_values = [3, 5, 8]
runs = {}
for k in k_values:
    runs[k] = json.load(open(RESULTS_DIR / f"run_k{k}_test.json", encoding="utf-8"))

print("\n" + "="*80)
print("AUDIT: PER-QUESTION RETRIEVAL RANKS AND RECALCULATIONS")
print("="*80)

for k in k_values:
    data = runs[k]
    print(f"\n--- CONDITION k={k} ---")
    
    # Check matching of questions
    q_ids = [r["question_id"] for r in data]
    assert q_ids == [q["question_id"] for q in test_queries], f"Mismatch in question order for k={k}"
    
    # Separate categories
    single_doc = [r for r in data if r["category"] == "sufficient_single"]
    multi_doc = [r for r in data if r["category"] == "sufficient_multi"]
    partial_doc = [r for r in data if r["category"] == "partial"]
    insufficient_doc = [r for r in data if r["category"] == "insufficient"]
    
    answerable_and_partial = single_doc + multi_doc + partial_doc
    
    print(f"Question counts: Single={len(single_doc)}, Multi={len(multi_doc)}, Partial={len(partial_doc)}, Insufficient={len(insufficient_doc)}")
    
    # Recalculate metrics directly from ground truth
    recalc_hits = []
    recalc_precisions = []
    recalc_recalls = []
    recalc_mrrs = []
    
    first_ranks = []
    
    for r in answerable_and_partial:
        qid = r["question_id"]
        gt_chunks = set(gt_by_id[qid]["ground_truth_chunk_ids"])
        ret_chunks = r["retrieved_chunk_ids"]
        
        # Intersection
        matched = [c for c in ret_chunks if c in gt_chunks]
        hit = 1.0 if len(matched) > 0 else 0.0
        prec = len(matched) / float(k)
        rec = len(matched) / float(len(gt_chunks)) if len(gt_chunks) > 0 else 0.0
        
        # First rank
        mrr = 0.0
        rank_found = None
        for rank_idx, c in enumerate(ret_chunks, start=1):
            if c in gt_chunks:
                mrr = 1.0 / rank_idx
                rank_found = rank_idx
                break
                
        first_ranks.append((qid, rank_found, mrr))
        recalc_hits.append(hit)
        recalc_precisions.append(prec)
        recalc_recalls.append(rec)
        recalc_mrrs.append(mrr)
        
    print(f"Recalculated Retrieval Metrics (N={len(answerable_and_partial)} answerable+partial):")
    print(f"  Hit Rate @ k:   {sum(recalc_hits)/len(recalc_hits):.4f}")
    print(f"  Precision @ k:  {sum(recalc_precisions)/len(recalc_precisions):.4f}")
    print(f"  Recall @ k:     {sum(recalc_recalls)/len(recalc_recalls):.4f}")
    print(f"  MRR:            {sum(recalc_mrrs)/len(recalc_mrrs):.4f}")
    
    # Check single-doc recall
    s_recalls = []
    for r in single_doc:
        qid = r["question_id"]
        gt_chunks = set(gt_by_id[qid]["ground_truth_chunk_ids"])
        matched = [c for c in r["retrieved_chunk_ids"] if c in gt_chunks]
        s_recalls.append(len(matched) / float(len(gt_chunks)))
    print(f"  Single-doc Recall (N={len(single_doc)}): {sum(s_recalls)/len(s_recalls):.4f}")
    
    # Check multi-doc recall
    m_recalls = []
    for r in multi_doc:
        qid = r["question_id"]
        gt_chunks = set(gt_by_id[qid]["ground_truth_chunk_ids"])
        matched = [c for c in r["retrieved_chunk_ids"] if c in gt_chunks]
        m_recalls.append(len(matched) / float(len(gt_chunks)))
    print(f"  Multi-doc Recall (N={len(multi_doc)}):  {sum(m_recalls)/len(m_recalls):.4f}")
    
    # Check partial recall
    p_recalls = []
    for r in partial_doc:
        qid = r["question_id"]
        gt_chunks = set(gt_by_id[qid]["ground_truth_chunk_ids"])
        matched = [c for c in r["retrieved_chunk_ids"] if c in gt_chunks]
        p_recalls.append(len(matched) / float(len(gt_chunks)))
    print(f"  Partial-doc Recall (N={len(partial_doc)}): {sum(p_recalls)/len(p_recalls):.4f}")
    
    # Inspect first ranks to explain MRR = 0.9500
    print("  First relevant chunk ranks across the 20 queries:")
    ranks_summary = {}
    for qid, rank, mrr in first_ranks:
        ranks_summary[rank] = ranks_summary.get(rank, 0) + 1
    print(f"    Rank distribution: {ranks_summary}")
    for qid, rank, mrr in first_ranks:
        if rank != 1:
            print(f"    -> {qid}: first relevant chunk was at rank {rank} (mrr={mrr:.4f})")
