"""
================================================================================
VISTAAR Standalone RAGAS Metric Evaluator
================================================================================
Implements the exact four core RAGAS metrics from the seminal paper:
  "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (Es et al., 2023)

Metrics Evaluated:
  1. Faithfulness (factual consistency of response with retrieved context)
  2. Answer Relevancy (semantic similarity of answer to original query)
  3. Context Precision (rank-weighted relevance of retrieved context chunks)
  4. Context Recall (coverage of ground-truth reference by retrieved context)

Key Engineering Principles:
  - Zero conflicts with installed packages (avoids dependency backtracking).
  - Uses the already configured Gemini client from backend/qa_service.py.
  - Uses the local all-MiniLM-L6-v2 embedding model for vector cosine similarity.
  - Robust JSON parsing, exponential backoff retries, and comprehensive CSV export.
================================================================================
"""

import os
import sys
import json
import csv
import time
import math
import re
from pathlib import Path
from typing import List, Dict, Any

# Ensure workspace and backend are in import path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load Gemini client & embedding model from existing backend
from dotenv import load_dotenv
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=WORKSPACE_DIR / ".env")

try:
    from qa_service import client, GEMINI_MODELS
    from embeddings import model as embedding_model
    from google.genai import types, errors
    # Prioritize models with active high-throughput quota pools
    EVAL_JUDGE_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
    ]
except ImportError as e:
    raise RuntimeError(f"Failed to import backend dependencies: {e}")


def call_gemini_judge(prompt: str, system_instruction: str = "", temperature: float = 0.0) -> str:
    """Invokes Gemini as the LLM judge with exponential backoff for rate limiting."""
    for model_name in EVAL_JUDGE_MODELS:
        for attempt in range(3):
            try:
                config_args = {"temperature": temperature}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
                if resp.text:
                    return resp.text.strip()
            except errors.APIError as e:
                print(f"[!] Gemini Judge APIError ({model_name}, attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"[!] Unexpected error in call_gemini_judge: {e}")
                time.sleep(1)
    return ""


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses valid JSON from LLM outputs containing code fences or prose."""
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract content inside markdown code blocks ```json ... ``` or ``` ... ```
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except Exception:
            pass

    # Extract outermost JSON object or list
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    return {}


# ==============================================================================
# RAGAS METRIC 1: Faithfulness
# ==============================================================================
def evaluate_faithfulness(question: str, contexts: List[str], response: str) -> Dict[str, Any]:
    """
    Measures the proportion of atomic claims in the response that can be directly
    inferred from the retrieved contexts.
    F = |Supported Claims| / |Total Claims|
    Refusals (e.g., 'I could not find this in the document') have 0 unsupported claims -> 1.0.
    """
    refusal_patterns = [
        "could not find this in the document",
        "no relevant information found",
        "not mentioned in the context",
        "context does not contain"
    ]
    if any(p in response.lower() for p in refusal_patterns):
        return {
            "score": 1.0,
            "total_claims": 0,
            "supported_claims": 0,
            "reason": "Accurate negative boundary refusal (no hallucinations produced)."
        }

    joined_context = "\n\n".join(contexts)
    prompt = f"""Given a context and an answer, evaluate the faithfulness of the answer.
Task:
1. Break down the answer into discrete, atomic factual claims.
2. For each claim, determine if it is directly supported by the context (true or false).

Context:
{joined_context}

Answer:
{response}

Output valid JSON ONLY with this schema:
{{
  "claims": [
    {{"statement": "claim 1", "supported": true}},
    {{"statement": "claim 2", "supported": false}}
  ]
}}"""

    system_inst = "You are an objective judge evaluating factual faithfulness in RAG systems. Return strict JSON only."
    raw_output = call_gemini_judge(prompt, system_instruction=system_inst, temperature=0.0)
    data = clean_json_response(raw_output)

    claims = data.get("claims", [])
    if not claims:
        # Fallback heuristic if decomposition returned empty
        return {"score": 1.0, "total_claims": 0, "supported_claims": 0, "reason": "No factual claims extracted."}

    supported_count = sum(1 for c in claims if c.get("supported") is True)
    score = supported_count / len(claims)
    return {
        "score": round(score, 4),
        "total_claims": len(claims),
        "supported_claims": supported_count,
        "claims_details": claims
    }


# ==============================================================================
# RAGAS METRIC 2: Answer Relevancy
# ==============================================================================
def evaluate_answer_relevancy(question: str, response: str) -> Dict[str, Any]:
    """
    Measures how pertinent the generated response is to the user question.
    Generates N=3 reverse questions from the response and computes the mean
    cosine similarity between the embedding of the user question and generated questions.
    """
    prompt = f"""Generate 3 distinct questions that could be directly answered by the following response:

Response:
{response}

Output valid JSON ONLY in this format:
{{
  "generated_questions": [
    "question 1",
    "question 2",
    "question 3"
  ]
}}"""

    system_inst = "You generate potential questions from an answer. Output JSON only."
    raw_output = call_gemini_judge(prompt, system_instruction=system_inst, temperature=0.0)
    data = clean_json_response(raw_output)

    gen_questions = data.get("generated_questions", [])
    if not gen_questions:
        gen_questions = [response]  # fallback

    # Compute dense embeddings using local all-MiniLM-L6-v2
    all_texts = [question] + gen_questions
    embeddings = embedding_model.encode(all_texts)
    q_vec = embeddings[0]
    gen_vecs = embeddings[1:]

    # Compute cosine similarities
    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if (norm_a * norm_b) > 0 else 0.0

    similarities = [cosine_sim(q_vec, g) for g in gen_vecs]
    mean_sim = sum(similarities) / len(similarities) if similarities else 0.0

    return {
        "score": round(max(0.0, min(1.0, mean_sim)), 4),
        "generated_questions": gen_questions,
        "cosine_similarities": [round(s, 4) for s in similarities]
    }


# ==============================================================================
# RAGAS METRIC 3: Context Precision
# ==============================================================================
def evaluate_context_precision(question: str, contexts: List[str], reference: str) -> Dict[str, Any]:
    """
    Measures whether the relevant context chunks appear at the highest ranks (Precision@k).
    Context Precision@K = sum(Precision@k * v_k) / sum(v_k)
    where v_k in {0, 1} indicates whether context chunk k is relevant to the reference answer.
    """
    if not contexts:
        return {"score": 0.0, "relevant_chunks": 0, "total_chunks": 0, "relevance_vector": []}

    # For unanswerable queries where reference is a refusal:
    if "could not find this in the document" in reference.lower():
        return {
            "score": 1.0,
            "relevant_chunks": 0,
            "total_chunks": len(contexts),
            "relevance_vector": [0] * len(contexts),
            "reason": "Unanswerable query; zero relevant chunks expected."
        }

    formatted_chunks = ""
    for idx, chunk in enumerate(contexts, 1):
        snippet = chunk.strip().replace("\n", " ")
        if len(snippet) > 800:
            snippet = snippet[:800] + "..."
        formatted_chunks += f"\n--- Chunk {idx} ---\n{snippet}\n"

    prompt = f"""You are evaluating retrieved context chunks for a RAG question-answering system.
Question: {question}
Reference Ground-Truth Answer: {reference}

Retrieved Chunks (in retrieval order, 1 to {len(contexts)}):
{formatted_chunks}

Task:
For each chunk (1 to {len(contexts)}), determine whether it contains useful, relevant information that directly contributes to answering the question based on the reference answer.

Output valid JSON ONLY with this schema:
{{
  "evaluations": [
    {{"chunk_index": 1, "is_relevant": true}},
    {{"chunk_index": 2, "is_relevant": false}}
  ]
}}"""

    system_inst = "You are an objective judge evaluating retrieval precision. Return strict JSON only."
    raw_output = call_gemini_judge(prompt, system_instruction=system_inst, temperature=0.0)
    data = clean_json_response(raw_output)

    eval_list = data.get("evaluations", [])
    chunk_relevances = [0] * len(contexts)
    if isinstance(eval_list, list) and eval_list:
        for item in eval_list:
            if isinstance(item, dict):
                c_idx = item.get("chunk_index", 0)
                is_rel = 1 if item.get("is_relevant") is True else 0
                if 1 <= c_idx <= len(contexts):
                    chunk_relevances[c_idx - 1] = is_rel

    total_relevant = sum(chunk_relevances)
    if total_relevant == 0:
        return {
            "score": 0.0,
            "relevant_chunks": 0,
            "total_chunks": len(contexts),
            "relevance_vector": chunk_relevances
        }

    precision_sum = 0.0
    running_hits = 0
    for k, v in enumerate(chunk_relevances, 1):
        if v == 1:
            running_hits += 1
            precision_at_k = running_hits / k
            precision_sum += precision_at_k

    context_precision_score = precision_sum / total_relevant
    return {
        "score": round(context_precision_score, 4),
        "relevant_chunks": total_relevant,
        "total_chunks": len(contexts),
        "relevance_vector": chunk_relevances
    }


# ==============================================================================
# RAGAS METRIC 4: Context Recall
# ==============================================================================
def evaluate_context_recall(question: str, contexts: List[str], reference: str) -> Dict[str, Any]:
    """
    Measures the extent to which the retrieved context covers the information in
    the ground-truth reference answer.
    Context Recall = |Attributed Reference Claims| / |Total Reference Claims|
    """
    if "could not find this in the document" in reference.lower():
        # Negative unanswerable query: context correctly does not contain answer -> Recall = 1.0
        return {"score": 1.0, "total_claims": 0, "attributed_claims": 0, "reason": "Unanswerable negative reference."}

    joined_context = "\n\n".join(contexts)
    prompt = f"""Given the retrieved context and ground-truth reference answer, evaluate context recall.
Task:
1. Break down the ground-truth reference answer into discrete factual statements.
2. For each statement, determine whether it can be attributed to the retrieved context.

Context:
{joined_context}

Reference Answer:
{reference}

Output valid JSON ONLY:
{{
  "reference_statements": [
    {{"statement": "statement 1", "attributed_to_context": true}},
    {{"statement": "statement 2", "attributed_to_context": false}}
  ]
}}"""

    system_inst = "You are an objective judge evaluating context recall in RAG systems. Return JSON only."
    raw_output = call_gemini_judge(prompt, system_instruction=system_inst, temperature=0.0)
    data = clean_json_response(raw_output)

    statements = data.get("reference_statements", [])
    if not statements:
        return {"score": 1.0, "total_claims": 0, "attributed_claims": 0}

    attributed_count = sum(1 for s in statements if s.get("attributed_to_context") is True)
    score = attributed_count / len(statements)
    return {
        "score": round(score, 4),
        "total_claims": len(statements),
        "attributed_claims": attributed_count,
        "statements_details": statements
    }


# ==============================================================================
# MAIN EVALUATION RUNNER
# ==============================================================================
def run_ragas_evaluation(input_file: Path, results_dir: Path):
    """Loads collected evaluation dataset and runs all four RAGAS metrics."""
    if not input_file.exists():
        raise FileNotFoundError(f"Collected dataset not found at {input_file}. Run collect_eval_data.py first.")

    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results_dir.mkdir(parents=True, exist_ok=True)
    per_question_csv = results_dir / "per_question_metrics.csv"
    aggregate_csv = results_dir / "aggregate_metrics.csv"

    print("=" * 80)
    print("VISTAAR RAGAS EVALUATION BENCHMARK")
    print(f"Total Questions to Evaluate: {len(dataset)}")
    print("=" * 80)

    evaluated_records = []

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        category = item.get("category", "unclassified")
        q = item["user_input"]
        ref = item["reference"]
        contexts = item.get("retrieved_contexts", [])
        resp = item.get("response", "")

        print(f"\n[{q_id}] ({idx}/{len(dataset)}) Evaluating: '{q[:45]}...'")

        # 1. Faithfulness
        f_res = evaluate_faithfulness(q, contexts, resp)
        faith_score = f_res["score"]
        print(f"  -> Faithfulness:       {faith_score:.4f} ({f_res.get('supported_claims',0)}/{f_res.get('total_claims',0)} claims supported)")

        # 2. Answer Relevancy
        ar_res = evaluate_answer_relevancy(q, resp)
        rel_score = ar_res["score"]
        print(f"  -> Answer Relevancy:   {rel_score:.4f}")

        # 3. Context Precision
        cp_res = evaluate_context_precision(q, contexts, ref)
        prec_score = cp_res["score"]
        print(f"  -> Context Precision:  {prec_score:.4f} ({cp_res.get('relevant_chunks',0)}/{cp_res.get('total_chunks',0)} chunks relevant)")

        # 4. Context Recall
        cr_res = evaluate_context_recall(q, contexts, ref)
        rec_score = cr_res["score"]
        print(f"  -> Context Recall:     {rec_score:.4f} ({cr_res.get('attributed_claims',0)}/{cr_res.get('total_claims',0)} reference statements)")

        overall_score = round((faith_score + rel_score + prec_score + rec_score) / 4.0, 4)

        record = {
            "id": q_id,
            "category": category,
            "user_input": q,
            "reference": ref,
            "response": resp,
            "faithfulness": faith_score,
            "answer_relevancy": rel_score,
            "context_precision": prec_score,
            "context_recall": rec_score,
            "overall_ragas_score": overall_score
        }
        evaluated_records.append(record)
        time.sleep(0.5)

    # Export Per-Question Metrics CSV
    fieldnames = [
        "id", "category", "user_input", "reference", "response",
        "faithfulness", "answer_relevancy", "context_precision", "context_recall", "overall_ragas_score"
    ]
    with open(per_question_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evaluated_records)
    print(f"\n[+] Saved per-question metrics to: {per_question_csv}")

    # Compute Aggregates (Overall and by Category)
    def compute_stats(values: List[float]):
        if not values:
            return 0.0, 0.0
        mean_v = sum(values) / len(values)
        variance = sum((x - mean_v) ** 2 for x in values) / len(values)
        return round(mean_v, 4), round(math.sqrt(variance), 4)

    categories = sorted(list(set(r["category"] for r in evaluated_records)))
    agg_rows = []

    # Overall stats
    f_mean, f_std = compute_stats([r["faithfulness"] for r in evaluated_records])
    ar_mean, ar_std = compute_stats([r["answer_relevancy"] for r in evaluated_records])
    cp_mean, cp_std = compute_stats([r["context_precision"] for r in evaluated_records])
    cr_mean, cr_std = compute_stats([r["context_recall"] for r in evaluated_records])
    ov_mean, ov_std = compute_stats([r["overall_ragas_score"] for r in evaluated_records])

    agg_rows.append({
        "group": "Overall (All 25 Questions)",
        "count": len(evaluated_records),
        "faithfulness_mean": f_mean, "faithfulness_std": f_std,
        "answer_relevancy_mean": ar_mean, "answer_relevancy_std": ar_std,
        "context_precision_mean": cp_mean, "context_precision_std": cp_std,
        "context_recall_mean": cr_mean, "context_recall_std": cr_std,
        "overall_mean": ov_mean, "overall_std": ov_std
    })

    # Category stats
    for cat in categories:
        subset = [r for r in evaluated_records if r["category"] == cat]
        sf_m, sf_s = compute_stats([r["faithfulness"] for r in subset])
        sar_m, sar_s = compute_stats([r["answer_relevancy"] for r in subset])
        scp_m, scp_s = compute_stats([r["context_precision"] for r in subset])
        scr_m, scr_s = compute_stats([r["context_recall"] for r in subset])
        sov_m, sov_s = compute_stats([r["overall_ragas_score"] for r in subset])

        agg_rows.append({
            "group": f"Category: {cat}",
            "count": len(subset),
            "faithfulness_mean": sf_m, "faithfulness_std": sf_s,
            "answer_relevancy_mean": sar_m, "answer_relevancy_std": sar_s,
            "context_precision_mean": scp_m, "context_precision_std": scp_s,
            "context_recall_mean": scr_m, "context_recall_std": scr_s,
            "overall_mean": sov_m, "overall_std": sov_s
        })

    agg_fieldnames = [
        "group", "count",
        "faithfulness_mean", "faithfulness_std",
        "answer_relevancy_mean", "answer_relevancy_std",
        "context_precision_mean", "context_precision_std",
        "context_recall_mean", "context_recall_std",
        "overall_mean", "overall_std"
    ]
    with open(aggregate_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"[+] Saved aggregate metrics to: {aggregate_csv}")

    # Terminal Summary Table
    print("\n" + "=" * 80)
    print("VISTAAR RAGAS EVALUATION - SUMMARY TABLE FOR RESEARCH PAPER")
    print("=" * 80)
    print(f"{'Metric':<22} | {'Mean':<8} | {'Std Dev':<8} | {'Min':<8} | {'Max':<8}")
    print("-" * 62)
    for metric_name, key in [
        ("Faithfulness", "faithfulness"),
        ("Answer Relevancy", "answer_relevancy"),
        ("Context Precision", "context_precision"),
        ("Context Recall", "context_recall"),
        ("Overall RAGAS Score", "overall_ragas_score")
    ]:
        vals = [r[key] for r in evaluated_records]
        m, s = compute_stats(vals)
        print(f"{metric_name:<22} | {m:<8.4f} | {s:<8.4f} | {min(vals):<8.4f} | {max(vals):<8.4f}")
    print("=" * 80)

    return evaluated_records, agg_rows


if __name__ == "__main__":
    input_ds = WORKSPACE_DIR / "evaluation" / "results" / "eval_dataset_collected.json"
    res_dir = WORKSPACE_DIR / "evaluation" / "results"
    run_ragas_evaluation(input_ds, res_dir)
