"""
validate_audit.py -- Task 3
Validates and summarises evaluation/results/real_pdf/manual_evidence_audit.csv.

Rules:
- Blank human_relevance rows are SKIPPED -- never counted as failures or successes.
- Results are broken down by category.
- Valid human_relevance values: yes, no, partial (case-insensitive).
- Valid answer_support values: yes, no, partial (case-insensitive).
- Warnings are emitted when reviewed < total or when invalid values are found.

Usage (run from project root):
    python evaluation/runners/validate_audit.py
"""
from __future__ import annotations
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = ROOT / "evaluation" / "results" / "real_pdf" / "manual_evidence_audit.csv"

VALID_RELEVANCE = {"yes", "no", "partial"}
VALID_SUPPORT = {"yes", "no", "partial"}

CATEGORIES = ["DSA", "Spring Boot", "CSS", "Cross-doc", "Unanswerable"]


def load_audit(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"ERROR: Audit file not found: {path}")
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def summarise(rows: list[dict]) -> None:
    total = len(rows)
    reviewed = [r for r in rows if r["human_relevance"].strip() != ""]
    skipped = total - len(reviewed)

    print("=" * 60)
    print("VISTAAR Real-PDF Evidence Audit Summary")
    print(f"Audit file: {AUDIT_FILE}")
    print("=" * 60)
    print(f"Total questions : {total}")
    print(f"Reviewed        : {len(reviewed)}")
    print(f"Skipped (blank) : {skipped}")
    if skipped > 0:
        print(f"  [WARNING] {skipped} question(s) not yet reviewed -- excluded from all statistics.")
    print()

    if not reviewed:
        print("No reviewed rows. Fill in human_relevance in the CSV and re-run.")
        return

    # Validate values
    invalid_rel = [r for r in reviewed if r["human_relevance"].strip().lower() not in VALID_RELEVANCE]
    invalid_sup = [r for r in reviewed if r["answer_support"].strip() != "" and
                   r["answer_support"].strip().lower() not in VALID_SUPPORT]
    if invalid_rel:
        print(f"[WARNING] {len(invalid_rel)} row(s) have invalid human_relevance value(s):")
        for r in invalid_rel:
            print(f"  {r['question_id']}: '{r['human_relevance']}'  (expected: yes/no/partial)")
    if invalid_sup:
        print(f"[WARNING] {len(invalid_sup)} row(s) have invalid answer_support value(s):")
        for r in invalid_sup:
            print(f"  {r['question_id']}: '{r['answer_support']}'  (expected: yes/no/partial or blank)")

    # Overall distributions
    rel_counts = Counter(r["human_relevance"].strip().lower() for r in reviewed)
    sup_filled = [r for r in reviewed if r["answer_support"].strip() != ""]
    sup_counts = Counter(r["answer_support"].strip().lower() for r in sup_filled)

    print("--- Overall (reviewed only) ---")
    print("Evidence Relevance distribution:")
    for val in ["yes", "partial", "no"]:
        n = rel_counts.get(val, 0)
        pct = 100 * n / len(reviewed) if reviewed else 0
        print(f"  {val:7s}: {n:3d}  ({pct:.1f}%)")

    if sup_filled:
        print("Answer Support distribution (among rows with answer_support filled):")
        for val in ["yes", "partial", "no"]:
            n = sup_counts.get(val, 0)
            pct = 100 * n / len(sup_filled) if sup_filled else 0
            print(f"  {val:7s}: {n:3d}  ({pct:.1f}%)")
    else:
        print("Answer Support: not yet filled in.")
    print()

    # Per-category breakdown
    print("--- Per-Category Breakdown ---")
    for cat in CATEGORIES:
        cat_all = [r for r in rows if r["category"] == cat]
        cat_rev = [r for r in cat_all if r["human_relevance"].strip() != ""]
        if not cat_all:
            continue
        print(f"\n  [{cat}]  total={len(cat_all)}, reviewed={len(cat_rev)}")
        if not cat_rev:
            print("    No reviewed rows yet.")
            continue
        rel_c = Counter(r["human_relevance"].strip().lower() for r in cat_rev)
        sup_c_rows = [r for r in cat_rev if r["answer_support"].strip() != ""]
        sup_c = Counter(r["answer_support"].strip().lower() for r in sup_c_rows)
        print(f"    Relevance: yes={rel_c.get('yes',0)}, partial={rel_c.get('partial',0)}, no={rel_c.get('no',0)}")
        if sup_c_rows:
            print(f"    Support  : yes={sup_c.get('yes',0)}, partial={sup_c.get('partial',0)}, no={sup_c.get('no',0)}")

    print()
    print("=" * 60)
    print("NOTE: These are human reviewer judgments on retrieval evidence quality.")
    print("They are NOT automated metrics. Do not describe them as precision/recall.")
    print("=" * 60)


def main() -> None:
    rows = load_audit(AUDIT_FILE)
    summarise(rows)


if __name__ == "__main__":
    main()
