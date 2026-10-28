"""
Generate aggregate metrics v2 and failures/refusals JSON from per_question_metrics_v2.csv
using unbiased sample standard deviation (N - 1) and explicit sample counts.
"""

import csv
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
AUDIT_V2_DIR = WORKSPACE_DIR / "evaluation" / "results" / "audit_v2"
PER_Q_CSV = AUDIT_V2_DIR / "per_question_metrics_v2.csv"
AGG_CSV = AUDIT_V2_DIR / "aggregate_metrics_v2.csv"
FAILURES_JSON = AUDIT_V2_DIR / "failures_and_refusals.json"


def compute_sample_stats(values: List[Optional[float]]) -> Dict[str, Any]:
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


def parse_float(val: str) -> Optional[float]:
    if val is None or val.strip() == "" or val.strip().lower() in ("none", "n/a", "nan"):
        return None
    try:
        return float(val)
    except ValueError:
        return None


def parse_bool(val: str) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("true", "1", "yes")


def generate_aggregates():
    with open(PER_Q_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    records = []
    failure_log = []

    for r in rows:
        rec = {
            "id": r["id"],
            "category": r["category"],
            "user_input": r["user_input"],
            "reference": r["reference"],
            "response": r["response"],
            "faithfulness_status": r["faithfulness_status"],
            "faithfulness_factual": parse_float(r["faithfulness_factual"]),
            "faithfulness_policy": parse_float(r["faithfulness_policy"]),
            "is_pure_refusal": parse_bool(r["is_pure_refusal"]),
            "answer_relevancy_status": r["answer_relevancy_status"],
            "answer_relevancy": parse_float(r["answer_relevancy"]),
            "context_precision_status": r["context_precision_status"],
            "context_precision": parse_float(r["context_precision"]),
            "context_recall_status": r["context_recall_status"],
            "context_recall_factual": parse_float(r["context_recall_factual"]),
            "context_recall_policy": parse_float(r["context_recall_policy"]),
            "is_negative_control": parse_bool(r["is_negative_control"])
        }
        records.append(rec)

        # Check failures
        for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            if rec.get(f"{metric}_status") == "FAILED":
                failure_log.append({"id": rec["id"], "metric": metric})

    # Save failures_and_refusals.json
    with open(FAILURES_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "total_questions": len(records),
            "total_failures": len(failure_log),
            "failures": failure_log,
            "pure_refusals_count": sum(1 for r in records if r["is_pure_refusal"]),
            "negative_controls_count": sum(1 for r in records if r["is_negative_control"]),
            "records": records
        }, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved {FAILURES_JSON}")

    # Build stat rows
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
    agg_rows.append(build_stat_row("Overall (All 25 Questions)", records))

    for cat in ["sufficient_evidence", "partial_evidence", "insufficient_evidence"]:
        sub = [r for r in records if r["category"] == cat]
        agg_rows.append(build_stat_row(f"Category: {cat}", sub))

    factual_sub = [r for r in records if not r["is_pure_refusal"]]
    refusal_sub = [r for r in records if r["is_pure_refusal"]]
    agg_rows.append(build_stat_row("Subset: Factual Answers (Claims > 0)", factual_sub))
    agg_rows.append(build_stat_row("Subset: Pure Refusals (Zero Claims)", refusal_sub))

    agg_fieldnames = [
        "group", "total_questions",
        "faithfulness_factual_n", "faithfulness_factual_mean", "faithfulness_factual_std", "faithfulness_policy_mean",
        "answer_relevancy_n", "answer_relevancy_mean", "answer_relevancy_std",
        "context_precision_n", "context_precision_mean", "context_precision_std",
        "context_recall_factual_n", "context_recall_factual_mean", "context_recall_factual_std", "context_recall_policy_mean"
    ]

    with open(AGG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"[+] Saved {AGG_CSV}")


if __name__ == "__main__":
    generate_aggregates()
