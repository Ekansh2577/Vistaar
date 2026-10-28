"""
================================================================================
VISTAAR Phase 2 Benchmark Runner (Top-k = 3, 5, 8 Ablation Suite)
================================================================================
Executes the controlled top-k ablation experiments across the Phase 2 benchmark
corpus without modifying any backend or frontend code.

Features:
- Ingests all 5 Phase 2 corpus documents (62 chunks total) using the exact
  unmodified backend pipeline (chunking, all-MiniLM-L6-v2, IndexFlatL2).
- Evaluates top-k retrieval conditions (k in [3, 5, 8]).
- Records deterministic retrieval metrics (Hit@k, Precision@k, Recall@k, MRR)
  independent of LLM generation.
- Records generation latency, token counts, retrieved chunk IDs, and model answers.
- Preserves all historical evaluation artifacts; outputs stored strictly in
  evaluation/results/phase2/.
================================================================================
"""

import os
import sys
import json
import csv
import time
import argparse
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure environment variables are loaded
from dotenv import load_dotenv
env_backend = BACKEND_DIR / ".env"
env_root = WORKSPACE_DIR / ".env"
if env_backend.exists():
    load_dotenv(dotenv_path=env_backend)
elif env_root.exists():
    load_dotenv(dotenv_path=env_root)

# Import unmodified backend components
try:
    from chunking import chunk_text
    from embeddings import get_embeddings, model
    from vector_store import add_to_index, search, index, stored_chunks
    from qa_service import ask_gemini
    import qa_service
    # Runtime optimization: prioritize active flash-lite models with available quota
    qa_service.GEMINI_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
    ]
except ImportError as e:
    raise RuntimeError(f"Failed to import backend modules from {BACKEND_DIR}: {e}")

EVAL_DIR = WORKSPACE_DIR / "evaluation"
CORPUS_DIR = EVAL_DIR / "corpus"
DATASETS_DIR = EVAL_DIR / "datasets"
RESULTS_PHASE2_DIR = EVAL_DIR / "results" / "phase2"


def initialize_phase2_index(manifest_path: Path):
    """
    Ingests all 5 documents listed in corpus_manifest.json into FAISS
    using the exact backend chunking and embedding configuration.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Corpus manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Reset any existing index state cleanly
    index.reset()
    stored_chunks.clear()

    print("[*] Ingesting Phase 2 Corpus Documents into FAISS IndexFlatL2...")
    total_ingested_chunks = 0
    chunk_metadata_lookup = []

    for doc_name, doc_meta in manifest["documents"].items():
        doc_path = CORPUS_DIR / doc_name
        with open(doc_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Backend chunking
        doc_chunks = chunk_text(text, size=1000, overlap=200)
        print(f"  - Ingesting {doc_name}: {len(doc_chunks)} chunks...", flush=True)

        # Generate embeddings via SentenceTransformer
        embeddings = get_embeddings(doc_chunks)

        # Add to FAISS index
        add_to_index(embeddings, doc_chunks)

        for idx, ch in enumerate(doc_chunks):
            cid = f"{doc_name.replace('.txt', '')}_c{idx:02d}"
            chunk_metadata_lookup.append({
                "chunk_id": cid,
                "doc_name": doc_name,
                "idx": idx,
                "text": ch
            })
        total_ingested_chunks += len(doc_chunks)

    print(f"[+] Successfully indexed {index.ntotal} vectors into FAISS (Total chunks: {total_ingested_chunks}).\n")
    return chunk_metadata_lookup


def compute_retrieval_metrics(retrieved_chunks, ground_truth_chunk_ids, chunk_metadata_lookup, k):
    """
    Computes deterministic retrieval metrics directly from FAISS results.
    """
    if not ground_truth_chunk_ids:
        # Unanswerable queries have no ground truth chunks
        return {
            "hit_at_k": None,
            "retrieval_precision": None,
            "retrieval_recall": None,
            "reciprocal_rank": None,
            "retrieved_chunk_ids": []
        }

    # Map retrieved chunk texts back to their assigned chunk IDs
    retrieved_cids = []
    for r_text in retrieved_chunks:
        matched_cid = None
        for meta in chunk_metadata_lookup:
            if meta["text"] == r_text:
                matched_cid = meta["chunk_id"]
                break
        retrieved_cids.append(matched_cid or "unknown")

    # Metrics calculation
    hits = [cid for cid in retrieved_cids if cid in ground_truth_chunk_ids]
    hit_at_k = 1.0 if len(hits) > 0 else 0.0
    precision = len(hits) / float(k)
    recall = len(hits) / float(len(ground_truth_chunk_ids)) if len(ground_truth_chunk_ids) > 0 else 0.0

    # Reciprocal rank (first relevant chunk)
    reciprocal_rank = 0.0
    for rank_idx, cid in enumerate(retrieved_cids, start=1):
        if cid in ground_truth_chunk_ids:
            reciprocal_rank = 1.0 / rank_idx
            break

    return {
        "hit_at_k": hit_at_k,
        "retrieval_precision": precision,
        "retrieval_recall": recall,
        "reciprocal_rank": reciprocal_rank,
        "retrieved_chunk_ids": retrieved_cids
    }


def run_ablation_experiment(split="test", k_values=(3, 5, 8), dry_run=False):
    """
    Runs the ablation experiment for specified top-k values across the selected split.
    """
    RESULTS_PHASE2_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CORPUS_DIR / "corpus_manifest.json"

    # Ingest corpus
    chunk_meta = initialize_phase2_index(manifest_path)

    # Load queries
    if split == "dev":
        queries_file = DATASETS_DIR / "tuning_queries.json"
    elif split == "test":
        queries_file = DATASETS_DIR / "test_queries_frozen.json"
    else:
        queries_file = DATASETS_DIR / "benchmark_queries_master.json"

    with open(queries_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    if dry_run:
        print("[!] DRY-RUN MODE: Restricting to first 2 queries without API execution.\n")
        queries = queries[:2]

    for k in k_values:
        print("=" * 80)
        print(f"EXECUTING EXPERIMENT CONDITION: top-k = {k} (Split: {split}, Questions: {len(queries)})")
        print("=" * 80)

        results = []
        for q_idx, q in enumerate(queries, start=1):
            qid = q["question_id"]
            question = q["question"]
            gt_chunk_ids = q["ground_truth_chunk_ids"]
            ref_ans = q["reference_answer"]
            cat = q["category"]

            print(f"[{q_idx:02d}/{len(queries):02d}] Processing {qid} ({cat})...", flush=True)

            # 1. Retrieval
            t0 = time.perf_counter()
            q_emb = model.encode([question])[0]
            retrieved_chunks = search(q_emb, k=k)
            retrieval_latency_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Retrieval metrics
            ret_metrics = compute_retrieval_metrics(retrieved_chunks, gt_chunk_ids, chunk_meta, k)

            # 3. Context & Prompt assembly (identical to qa_service)
            context_str = "\n\n---\n\n".join(retrieved_chunks)
            prompt = f"Context:\n{context_str}\n\nQuestion: {question}"

            # 4. Generation with error isolation
            is_api_failure = False
            api_error_message = None
            if dry_run:
                response = f"[DRY-RUN RESPONSE FOR {qid} WITH k={k}]"
                gen_latency_ms = 0.0
            else:
                t_gen = time.perf_counter()
                try:
                    response = ask_gemini(prompt)
                    gen_latency_ms = (time.perf_counter() - t_gen) * 1000.0
                    if not response:
                        is_api_failure = True
                        api_error_message = "Empty response returned by Gemini API"
                        response = "FAILED_API_CALL: Empty response returned by model cascade."
                except Exception as e:
                    gen_latency_ms = (time.perf_counter() - t_gen) * 1000.0
                    is_api_failure = True
                    api_error_message = str(e)
                    response = f"FAILED_API_CALL: {e}"

            # Estimated token counts & costs (Explicitly labeled as estimates)
            # Backend qa_service returns answer string without usage metadata.
            prompt_tokens_est = len(prompt) // 4
            response_tokens_est = len(response) // 4
            input_cost_est_usd = (prompt_tokens_est / 1_000_000.0) * 0.075
            output_cost_est_usd = (response_tokens_est / 1_000_000.0) * 0.300
            total_cost_est_usd = round(input_cost_est_usd + output_cost_est_usd, 6)

            record = {
                "question_id": qid,
                "category": cat,
                "k": k,
                "user_input": question,
                "reference": ref_ans,
                "retrieved_contexts": retrieved_chunks,
                "retrieved_chunk_ids": ret_metrics["retrieved_chunk_ids"],
                "response": response,
                "is_api_failure": is_api_failure,
                "api_error_message": api_error_message,
                "refusal_expected": q["refusal_expected"],
                "partial_scope": q.get("partial_scope"),
                "retrieval_latency_ms": round(retrieval_latency_ms, 2),
                "generation_latency_ms": round(gen_latency_ms, 2),
                "total_latency_ms": round(retrieval_latency_ms + gen_latency_ms, 2),
                "hit_at_k": ret_metrics["hit_at_k"],
                "retrieval_precision": ret_metrics["retrieval_precision"],
                "retrieval_recall": ret_metrics["retrieval_recall"],
                "reciprocal_rank": ret_metrics["reciprocal_rank"],
                "prompt_tokens_est": prompt_tokens_est,
                "response_tokens_est": response_tokens_est,
                "total_cost_est_usd": total_cost_est_usd,
                "token_measurement_type": "heuristic_estimate_4_chars_per_token"
            }
            results.append(record)

        # Output paths
        json_out = RESULTS_PHASE2_DIR / f"run_k{k}_{split}.json"
        csv_out = RESULTS_PHASE2_DIR / f"run_k{k}_{split}.csv"

        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # CSV output
        fieldnames = [
            "question_id", "category", "k", "user_input", "reference", "response",
            "is_api_failure", "api_error_message", "refusal_expected",
            "retrieval_latency_ms", "generation_latency_ms", "total_latency_ms",
            "hit_at_k", "retrieval_precision", "retrieval_recall", "reciprocal_rank",
            "prompt_tokens_est", "response_tokens_est", "total_cost_est_usd",
            "token_measurement_type", "retrieved_chunk_ids"
        ]
        with open(csv_out, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in results:
                row = dict(r)
                row["retrieved_chunk_ids"] = ";".join(row["retrieved_chunk_ids"])
                writer.writerow(row)

        print(f"[+] Completed Condition k={k}. Output written to:")
        print(f"    - JSON: {json_out}")
        print(f"    - CSV:  {csv_out}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VISTAAR Phase 2 Benchmark Runner")
    parser.add_argument("--split", choices=["test", "dev", "master"], default="test", help="Dataset split to evaluate")
    parser.add_argument("--k_values", nargs="+", type=int, default=[3, 5, 8], help="List of top-k values")
    parser.add_argument("--dry_run", action="store_true", help="Run in dry-run mode (no API calls)")
    args = parser.parse_args()

    run_ablation_experiment(split=args.split, k_values=args.k_values, dry_run=args.dry_run)
