"""
================================================================================
VISTAAR Corrected Evaluation Module (Phase 1 Audit v2)
================================================================================
Fixes Phase 1 audit issues identified in evaluation/results/audit_report.md:
  1. Zero Silent Defaults: Network/API failures are retried with bounded
     exponential backoff. If exhausted, marked as FAILED/None (never 1.0 or 0.0).
  2. Mixed Answer Parsing: Evaluates factual claims even when responses contain
     both factual answers and refusal strings (e.g., Q15).
  3. Transparent Refusal Policies: Explicitly distinguishes pure refusals from
     factual answers. Refusal questions are reported under explicit policies
     and separated from factual claim accuracy.
  4. Academic Sample Statistics: Uses unbiased sample standard deviation (N - 1)
     and reports valid sample counts (N_valid) for every metric.
  5. Isolated Execution: Does not modify original results or backend files;
     saves outputs to evaluation/results/audit_v2/.
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
from typing import List, Dict, Any, Optional, Tuple

# Workspace and backend paths
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load Gemini client & embedding model from backend
from dotenv import load_dotenv
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=WORKSPACE_DIR / ".env")

try:
    from qa_service import client, GEMINI_MODELS
    from embeddings import model as embedding_model
    from google.genai import types, errors
    # Candidate pool ordered by throughput & active quota
    EVAL_JUDGE_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
    ]
except ImportError as e:
    raise RuntimeError(f"Failed to import backend dependencies: {e}")


class JudgeCallError(Exception):
    """Raised when the LLM judge fails across all candidate models and retries."""
    pass


def call_gemini_judge_strict(prompt: str, system_instruction: str = "", temperature: float = 0.0) -> str:
    """
    Invokes Gemini judge with bounded exponential backoff across model pool.
    Raises JudgeCallError if all retries fail. NEVER silently returns empty string.
    """
    last_exception = None

    for model_name in EVAL_JUDGE_MODELS:
        # 3 attempts per model
        for attempt in range(1, 4):
            try:
                config_args = {"temperature": temperature}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction

                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
                if resp.text and resp.text.strip():
                    return resp.text.strip()
                else:
                    # Empty response body from model
                    last_exception = ValueError(f"Empty text returned by {model_name}")
            except errors.APIError as e:
                last_exception = e
                # Check for rate-limiting 429
                status_code = getattr(e, "code", None) or getattr(e, "status_code", None)
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Bounded exponential backoff: 3s, 6s, 12s
                    delay = min(15.0, 3.0 * (2 ** (attempt - 1)))
                    print(f"    [!] 429 RateLimit ({model_name}, attempt {attempt}): sleeping {delay:.1f}s...")
                    time.sleep(delay)
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    delay = min(10.0, 2.0 * (2 ** (attempt - 1)))
                    print(f"    [!] 503 Spike ({model_name}, attempt {attempt}): sleeping {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    time.sleep(1.5)
            except Exception as e:
                # Network socket error / connection drop
                last_exception = e
                print(f"    [!] Connection error ({model_name}, attempt {attempt}): {e}")
                time.sleep(2.0 * attempt)

    raise JudgeCallError(f"All candidate models exhausted. Last error: {last_exception}")


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses valid JSON from LLM outputs containing code fences or prose."""
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract inside code block ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Extract outermost { ... } or [ ... ]
    match_braces = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match_braces:
        try:
            return json.loads(match_braces.group(1).strip())
        except Exception:
            pass

    return {}


def is_pure_refusal(text: str) -> bool:
    """
    Checks if a text consists SOLELY of a negative boundary refusal statement.
    Does NOT match mixed answers that contain both factual content and refusal notes.
    """
    cleaned = text.strip().lower()
    # Normalize punctuation
    cleaned = re.sub(r'[\.\,\!\?\"\']', '', cleaned).strip()

    exact_refusal_phrases = [
        "i could not find this in the document",
        "could not find this in the document",
        "no relevant information found",
        "not mentioned in the document",
        "context does not contain the answer",
        "context does not contain this information"
    ]
    return cleaned in exact_refusal_phrases


# ==============================================================================
# CORRECTED METRIC 1: Faithfulness (Factual vs Refusal Policy)
# ==============================================================================
def evaluate_faithfulness_v2(question: str, contexts: List[str], response: str) -> Dict[str, Any]:
    """
    Evaluates faithfulness of factual claims against retrieved contexts.
    - If pure refusal: documents zero factual claims; factual_score is None, policy_score is 1.0.
    - If mixed answer or standard answer: extracts all factual claims, ignoring refusal phrases,
      and verifies each claim against context.
    - If API fails: returns status='FAILED', score=None (never silent 1.0).
    """
    if is_pure_refusal(response):
        return {
            "status": "SUCCESS",
            "is_pure_refusal": True,
            "total_claims": 0,
            "supported_claims": 0,
            "factual_score": None,          # Undefined (0/0)
            "policy_score": 1.0,            # Negative boundary compliance
            "claims_details": [],
            "reason": "Pure negative boundary refusal (zero factual claims asserted)."
        }

    joined_context = "\n\n".join(contexts)
    prompt = f"""You are evaluating the factual faithfulness of an answer in a RAG system.

Context:
{joined_context}

Answer to evaluate:
{response}

Task:
1. Extract all factual statements or claims asserted in the answer.
   (IMPORTANT: Ignore meta-refusal phrases like "I could not find this in the document" or "the document does not state").
2. For each extracted factual claim, determine whether it is directly supported by the context above (true or false).

Output valid JSON ONLY with this schema:
{{
  "claims": [
    {{"statement": "claim 1", "supported": true}},
    {{"statement": "claim 2", "supported": false}}
  ]
}}"""

    system_inst = "You are an objective judge evaluating factual faithfulness in RAG systems. Return strict JSON only."

    try:
        raw_output = call_gemini_judge_strict(prompt, system_instruction=system_inst, temperature=0.0)
    except JudgeCallError as e:
        return {
            "status": "FAILED",
            "is_pure_refusal": False,
            "total_claims": 0,
            "supported_claims": 0,
            "factual_score": None,
            "policy_score": None,
            "error": str(e)
        }

    data = clean_json_response(raw_output)
    claims = data.get("claims", [])

    if not claims:
        # Model returned no factual claims (e.g. meta commentary)
        return {
            "status": "SUCCESS",
            "is_pure_refusal": False,
            "total_claims": 0,
            "supported_claims": 0,
            "factual_score": None,
            "policy_score": 1.0,
            "claims_details": [],
            "reason": "No discrete factual claims extracted from response."
        }

    supported_count = sum(1 for c in claims if c.get("supported") is True)
    factual_score = round(supported_count / len(claims), 4)

    return {
        "status": "SUCCESS",
        "is_pure_refusal": False,
        "total_claims": len(claims),
        "supported_claims": supported_count,
        "factual_score": factual_score,
        "policy_score": factual_score,
        "claims_details": claims
    }


# ==============================================================================
# CORRECTED METRIC 2: Answer Relevancy
# ==============================================================================
def evaluate_answer_relevancy_v2(question: str, response: str) -> Dict[str, Any]:
    """
    Computes semantic similarity between the user question and n=3 reverse questions
    generated from the response using all-MiniLM-L6-v2 embeddings.
    If API fails: returns status='FAILED', score=None.
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

    try:
        raw_output = call_gemini_judge_strict(prompt, system_instruction=system_inst, temperature=0.0)
    except JudgeCallError as e:
        return {
            "status": "FAILED",
            "score": None,
            "error": str(e)
        }

    data = clean_json_response(raw_output)
    gen_questions = data.get("generated_questions", [])
    if not gen_questions:
        gen_questions = [response]

    # Compute dense embeddings using local all-MiniLM-L6-v2
    all_texts = [question] + gen_questions
    embeddings = embedding_model.encode(all_texts)
    q_vec = embeddings[0]
    gen_vecs = embeddings[1:]

    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        return dot / (norm_a * norm_b) if (norm_a * norm_b) > 0 else 0.0

    similarities = [cosine_sim(q_vec, g) for g in gen_vecs]
    mean_sim = sum(similarities) / len(similarities) if similarities else 0.0
    bounded_sim = round(max(0.0, min(1.0, mean_sim)), 4)

    return {
        "status": "SUCCESS",
        "score": bounded_sim,
        "is_pure_refusal": is_pure_refusal(response),
        "generated_questions": gen_questions,
        "cosine_similarities": [round(s, 4) for s in similarities]
    }


# ==============================================================================
# CORRECTED METRIC 3: Context Precision (Precision@K)
# ==============================================================================
def evaluate_context_precision_v2(question: str, contexts: List[str], reference: str) -> Dict[str, Any]:
    """
    Measures rank-weighted precision of retrieved chunks.
    - If unanswerable query (reference is pure refusal): marks as negative control.
    - If API fails: returns status='FAILED', score=None (never silent 0.0 or 1.0).
    """
    if not contexts:
        return {
            "status": "SUCCESS",
            "score": 0.0,
            "relevant_chunks": 0,
            "total_chunks": 0,
            "relevance_vector": [],
            "reason": "Empty context list."
        }

    # Identify if reference is a pure refusal (negative control test)
    ref_is_refusal = is_pure_refusal(reference) or ("could not find this in the document" in reference.lower())

    formatted_chunks = ""
    for idx, chunk in enumerate(contexts, 1):
        snippet = chunk.strip().replace("\n", " ")
        if len(snippet) > 800:
            snippet = snippet[:800] + "..."
        formatted_chunks += f"\n--- Chunk {idx} ---\n{snippet}\n"

    prompt = f"""You are evaluating retrieved context chunks for a RAG question-answering system.
Question: {question}
Reference Ground-Truth Answer: {reference}

Retrieved Chunks (in retrieval rank order, 1 to {len(contexts)}):
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

    try:
        raw_output = call_gemini_judge_strict(prompt, system_instruction=system_inst, temperature=0.0)
    except JudgeCallError as e:
        return {
            "status": "FAILED",
            "score": None,
            "error": str(e),
            "relevant_chunks": 0,
            "total_chunks": len(contexts)
        }

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
        if ref_is_refusal:
            # For negative controls, zero relevant chunks retrieved is the correct behavior
            return {
                "status": "SUCCESS",
                "is_negative_control": True,
                "score": 1.0,           # Negative control precision (no false positives)
                "score_strict": None,    # Formally 0/0
                "relevant_chunks": 0,
                "total_chunks": len(contexts),
                "relevance_vector": chunk_relevances,
                "reason": "Unanswerable query; zero relevant chunks expected and found."
            }
        else:
            return {
                "status": "SUCCESS",
                "is_negative_control": False,
                "score": 0.0,
                "score_strict": 0.0,
                "relevant_chunks": 0,
                "total_chunks": len(contexts),
                "relevance_vector": chunk_relevances,
                "reason": "No retrieved chunks contained relevant information."
            }

    # Compute rank-weighted precision: sum(Precision@k * v_k) / sum(v_k)
    precision_sum = 0.0
    running_hits = 0
    for k, v in enumerate(chunk_relevances, 1):
        if v == 1:
            running_hits += 1
            precision_at_k = running_hits / k
            precision_sum += precision_at_k

    context_precision_score = precision_sum / total_relevant

    return {
        "status": "SUCCESS",
        "is_negative_control": False,
        "score": round(context_precision_score, 4),
        "score_strict": round(context_precision_score, 4),
        "relevant_chunks": total_relevant,
        "total_chunks": len(contexts),
        "relevance_vector": chunk_relevances
    }


# ==============================================================================
# CORRECTED METRIC 4: Context Recall
# ==============================================================================
def evaluate_context_recall_v2(question: str, contexts: List[str], reference: str) -> Dict[str, Any]:
    """
    Measures the proportion of ground-truth reference statements covered by context.
    - If reference is pure refusal: marks as negative control (factual recall is N/A).
    - If API fails: returns status='FAILED', score=None (never silent 1.0).
    """
    ref_is_refusal = is_pure_refusal(reference) or ("could not find this in the document" in reference.lower())

    if ref_is_refusal:
        return {
            "status": "SUCCESS",
            "is_negative_control": True,
            "factual_score": None,       # Zero reference statements to retrieve
            "policy_score": 1.0,         # Negative boundary compliance
            "total_statements": 0,
            "attributed_statements": 0,
            "reason": "Unanswerable reference (zero factual statements expected in context)."
        }

    joined_context = "\n\n".join(contexts)
    prompt = f"""Given the retrieved context and ground-truth reference answer, evaluate context recall.

Context:
{joined_context}

Reference Answer:
{reference}

Task:
1. Break down the ground-truth reference answer into discrete factual statements.
2. For each statement, determine whether it can be attributed to the retrieved context above (true or false).

Output valid JSON ONLY with this schema:
{{
  "reference_statements": [
    {{"statement": "statement 1", "attributed_to_context": true}},
    {{"statement": "statement 2", "attributed_to_context": false}}
  ]
}}"""

    system_inst = "You are an objective judge evaluating context recall in RAG systems. Return strict JSON only."

    try:
        raw_output = call_gemini_judge_strict(prompt, system_instruction=system_inst, temperature=0.0)
    except JudgeCallError as e:
        return {
            "status": "FAILED",
            "is_negative_control": False,
            "factual_score": None,
            "policy_score": None,
            "error": str(e),
            "total_statements": 0,
            "attributed_statements": 0
        }

    data = clean_json_response(raw_output)
    statements = data.get("reference_statements", [])

    if not statements:
        return {
            "status": "SUCCESS",
            "is_negative_control": False,
            "factual_score": None,
            "policy_score": None,
            "total_statements": 0,
            "attributed_statements": 0,
            "reason": "No discrete statements extracted from reference answer."
        }

    attributed_count = sum(1 for s in statements if s.get("attributed_to_context") is True)
    recall_score = round(attributed_count / len(statements), 4)

    return {
        "status": "SUCCESS",
        "is_negative_control": False,
        "factual_score": recall_score,
        "policy_score": recall_score,
        "total_statements": len(statements),
        "attributed_statements": attributed_count,
        "statements_details": statements
    }


# ==============================================================================
# STATISTICAL UTILITY FUNCTIONS (Sample Standard Deviation N - 1)
# ==============================================================================
def compute_sample_stats(values: List[Optional[float]]) -> Dict[str, Any]:
    """Computes mean and sample standard deviation (Bessel's correction N - 1)."""
    valid = [v for v in values if v is not None and not math.isnan(v)]
    n = len(valid)
    if n == 0:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    mean_v = sum(valid) / n
    if n > 1:
        variance = sum((x - mean_v) ** 2 for x in valid) / (n - 1)
        std_v = math.sqrt(variance)
    else:
        std_v = 0.0
    return {
        "count": n,
        "mean": round(mean_v, 4),
        "std": round(std_v, 4),
        "min": round(min(valid), 4),
        "max": round(max(valid), 4)
    }


# ==============================================================================
# MAIN RUNNER FOR AUDIT V2
# ==============================================================================
def run_corrected_evaluation(input_file: Path, output_dir: Path):
    """Executes the corrected evaluation over the existing collected dataset."""
    if not input_file.exists():
        raise FileNotFoundError(f"Collected dataset not found at {input_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    per_question_csv = output_dir / "per_question_metrics_v2.csv"
    aggregate_csv = output_dir / "aggregate_metrics_v2.csv"
    failures_json = output_dir / "failures_and_refusals.json"

    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("=" * 80)
    print("VISTAAR CORRECTED EVALUATION RUNNER (Phase 1 Audit v2)")
    print(f"Total Questions to Evaluate: {len(dataset)}")
    print(f"Target Output Directory:     {output_dir}")
    print("=" * 80)

    evaluated_records = []
    failure_log = []

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        category = item.get("category", "unclassified")
        q = item["user_input"]
        ref = item["reference"]
        contexts = item.get("retrieved_contexts", [])
        resp = item.get("response", "")

        print(f"\n[{q_id}] ({idx}/{len(dataset)}) Category: {category} | Query: '{q[:40]}...'")

        # 1. Faithfulness
        f_res = evaluate_faithfulness_v2(q, contexts, resp)
        f_factual = f_res.get("factual_score")
        f_policy = f_res.get("policy_score")
        f_status = f_res["status"]
        if f_status == "FAILED":
            print(f"  [X] Faithfulness: FAILED ({f_res.get('error')})")
            failure_log.append({"id": q_id, "metric": "faithfulness", "error": f_res.get("error")})
        else:
            f_str = f"{f_factual:.4f}" if f_factual is not None else "N/A (Pure Refusal)"
            print(f"  -> Faithfulness (Factual): {f_str} | Claims: {f_res.get('supported_claims')}/{f_res.get('total_claims')}")

        # 2. Answer Relevancy
        ar_res = evaluate_answer_relevancy_v2(q, resp)
        ar_score = ar_res.get("score")
        ar_status = ar_res["status"]
        if ar_status == "FAILED":
            print(f"  [X] Answer Relevancy: FAILED ({ar_res.get('error')})")
            failure_log.append({"id": q_id, "metric": "answer_relevancy", "error": ar_res.get("error")})
        else:
            print(f"  -> Answer Relevancy:       {ar_score:.4f}")

        # 3. Context Precision
        cp_res = evaluate_context_precision_v2(q, contexts, ref)
        cp_score = cp_res.get("score")
        cp_status = cp_res["status"]
        if cp_status == "FAILED":
            print(f"  [X] Context Precision: FAILED ({cp_res.get('error')})")
            failure_log.append({"id": q_id, "metric": "context_precision", "error": cp_res.get("error")})
        else:
            cp_str = f"{cp_score:.4f}" if cp_score is not None else "N/A"
            print(f"  -> Context Precision:      {cp_str} (Hits: {cp_res.get('relevant_chunks')}/{cp_res.get('total_chunks')})")

        # 4. Context Recall
        cr_res = evaluate_context_recall_v2(q, contexts, ref)
        cr_factual = cr_res.get("factual_score")
        cr_policy = cr_res.get("policy_score")
        cr_status = cr_res["status"]
        if cr_status == "FAILED":
            print(f"  [X] Context Recall: FAILED ({cr_res.get('error')})")
            failure_log.append({"id": q_id, "metric": "context_recall", "error": cr_res.get("error")})
        else:
            cr_str = f"{cr_factual:.4f}" if cr_factual is not None else "N/A (Neg Control)"
            print(f"  -> Context Recall (Factual): {cr_str}")

        record = {
            "id": q_id,
            "category": category,
            "user_input": q,
            "reference": ref,
            "response": resp,
            "faithfulness_status": f_status,
            "faithfulness_factual": f_factual,
            "faithfulness_policy": f_policy,
            "is_pure_refusal": f_res.get("is_pure_refusal", False),
            "answer_relevancy_status": ar_status,
            "answer_relevancy": ar_score,
            "context_precision_status": cp_status,
            "context_precision": cp_score,
            "context_recall_status": cr_status,
            "context_recall_factual": cr_factual,
            "context_recall_policy": cr_policy,
            "is_negative_control": cr_res.get("is_negative_control", False)
        }
        evaluated_records.append(record)

        # Courtesy sleep to stay safely below 15 RPM limits
        time.sleep(1.0)

    # 1. Export Per-Question CSV
    fieldnames = [
        "id", "category", "user_input", "reference", "response",
        "faithfulness_status", "faithfulness_factual", "faithfulness_policy", "is_pure_refusal",
        "answer_relevancy_status", "answer_relevancy",
        "context_precision_status", "context_precision",
        "context_recall_status", "context_recall_factual", "context_recall_policy",
        "is_negative_control"
    ]
    with open(per_question_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evaluated_records)
    print(f"\n[+] Saved per-question metrics to: {per_question_csv}")

    # 2. Export Failures and Refusals JSON
    def json_serializer(o):
        if hasattr(o, '__float__'):
            return float(o)
        return str(o)

    with open(failures_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_questions": len(evaluated_records),
            "total_failures": len(failure_log),
            "failures": failure_log,
            "records": evaluated_records
        }, f, indent=2, ensure_ascii=False, default=json_serializer)
    print(f"[+] Saved failure and refusal audit log to: {failures_json}")

    # 3. Compute Aggregate Statistics by Group using Sample Statistics
    def build_stat_row(group_name: str, subset: List[Dict[str, Any]]) -> Dict[str, Any]:
        f_fact_stats = compute_sample_stats([r["faithfulness_factual"] for r in subset if r["faithfulness_status"] == "SUCCESS"])
        f_pol_stats = compute_sample_stats([r["faithfulness_policy"] for r in subset if r["faithfulness_status"] == "SUCCESS"])
        ar_stats = compute_sample_stats([r["answer_relevancy"] for r in subset if r["answer_relevancy_status"] == "SUCCESS"])
        cp_stats = compute_sample_stats([r["context_precision"] for r in subset if r["context_precision_status"] == "SUCCESS"])
        cr_fact_stats = compute_sample_stats([r["context_recall_factual"] for r in subset if r["context_recall_status"] == "SUCCESS"])
        cr_pol_stats = compute_sample_stats([r["context_recall_policy"] for r in subset if r["context_recall_status"] == "SUCCESS"])

        return {
            "group": group_name,
            "total_questions": len(subset),
            "faithfulness_factual_n": f_fact_stats["count"],
            "faithfulness_factual_mean": f_fact_stats["mean"],
            "faithfulness_factual_std": f_fact_stats["std"],
            "faithfulness_policy_mean": f_pol_stats["mean"],
            "answer_relevancy_n": ar_stats["count"],
            "answer_relevancy_mean": ar_stats["mean"],
            "answer_relevancy_std": ar_stats["std"],
            "context_precision_n": cp_stats["count"],
            "context_precision_mean": cp_stats["mean"],
            "context_precision_std": cp_stats["std"],
            "context_recall_factual_n": cr_fact_stats["count"],
            "context_recall_factual_mean": cr_fact_stats["mean"],
            "context_recall_factual_std": cr_fact_stats["std"],
            "context_recall_policy_mean": cr_pol_stats["mean"]
        }

    agg_rows = []
    # Overall
    agg_rows.append(build_stat_row("Overall (All Questions)", evaluated_records))

    # Categories
    for cat in ["sufficient_evidence", "partial_evidence", "insufficient_evidence"]:
        sub = [r for r in evaluated_records if r["category"] == cat]
        agg_rows.append(build_stat_row(f"Category: {cat}", sub))

    # Factual Answerable Subset vs Pure Refusal Subset
    factual_sub = [r for r in evaluated_records if not r["is_pure_refusal"]]
    refusal_sub = [r for r in evaluated_records if r["is_pure_refusal"]]
    agg_rows.append(build_stat_row("Subset: Factual Answers (Claims > 0)", factual_sub))
    agg_rows.append(build_stat_row("Subset: Pure Refusals (Zero Claims)", refusal_sub))

    agg_fieldnames = [
        "group", "total_questions",
        "faithfulness_factual_n", "faithfulness_factual_mean", "faithfulness_factual_std", "faithfulness_policy_mean",
        "answer_relevancy_n", "answer_relevancy_mean", "answer_relevancy_std",
        "context_precision_n", "context_precision_mean", "context_precision_std",
        "context_recall_factual_n", "context_recall_factual_mean", "context_recall_factual_std", "context_recall_policy_mean"
    ]
    with open(aggregate_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"[+] Saved corrected aggregate statistics to: {aggregate_csv}")

    return evaluated_records, agg_rows, failure_log


if __name__ == "__main__":
    input_data = WORKSPACE_DIR / "evaluation" / "results" / "eval_dataset_collected.json"
    out_dir = WORKSPACE_DIR / "evaluation" / "results" / "audit_v2"
    run_corrected_evaluation(input_data, out_dir)
