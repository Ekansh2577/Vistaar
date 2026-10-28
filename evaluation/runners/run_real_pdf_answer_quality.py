"""
run_real_pdf_answer_quality.py -- Task 4  (checkpoint/resume edition)
Standalone Gemini answer-quality evaluation for VISTAAR real PDFs.

What it does:
  1. Builds a fresh FAISS index from the three real PDFs (same pipeline as
     run_real_pdf_vistaar.py).
  2. For each of the 30 benchmark questions, retrieves k=5 chunks and calls
     the local ask_gemini_eval() wrapper.
  3. Checkpoints every completed question immediately to
     evaluation/results/real_pdf/answer_quality_checkpoint.jsonl
     so a partial run can be resumed without repeating API calls.
  4. Skips questions that already have a SUCCESSFUL answer in the checkpoint.
     API failures (quota / transient) are retried on the next run.
  5. Stops issuing further API calls if a daily-quota exhaustion is detected
     and saves all completed results before exiting.
  6. Writes final outputs only at aggregation time:
       answer_quality_raw.json
       answer_quality_summary.csv

What it does NOT do:
  - Does not modify backend/qa_service.py or any production code.
  - Does not print, log, or save the API key.
  - Does not call answer_question() (that uses the live production index).
  - Does not treat API failures as valid generated answers.
  - Does not overwrite existing retrieval results.

Usage (run from project root):
    python evaluation/runners/run_real_pdf_answer_quality.py

To resume after a quota reset or interruption:
    Just re-run the same command.  Questions already answered are skipped.
    To retry a failed question, delete its line from answer_quality_checkpoint.jsonl.
    To start completely fresh, delete answer_quality_checkpoint.jsonl.

Dependencies (already in backend/requirements.txt):
    PyPDF2, sentence-transformers, faiss-cpu, google-genai, python-dotenv
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DOCS = ROOT / "evaluation" / "real_docs"
OUT = ROOT / "evaluation" / "results" / "real_pdf"
QUESTION_FILE = ROOT / "evaluation" / "real_pdf_question_bank.json"
CHECKPOINT_FILE = OUT / "answer_quality_checkpoint.jsonl"

sys.path.insert(0, str(BACKEND))

# Heavy imports (embedding model) loaded lazily so syntax checks run instantly.
# API client is constructed inside ask_gemini_eval(); key never printed.
from PyPDF2 import PdfReader
from chunking import chunk_text
from embeddings import model as embed_model
import vector_store

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REFUSAL_PHRASE = "I could not find this in the document."
K_RETRIEVAL = 5
MAX_RETRIES = 3                           # retries per model
INTER_REQUEST_SLEEP = 2.0                 # seconds between questions
BACKOFF_BASE = 2                          # seconds for exponential back-off

# Models to try in order. Matches the production cascade in backend/qa_service.py.
EVAL_MODELS = [
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-3.5-flash",
]

# Keywords that identify a DAILY quota exhaustion (not a transient rate limit).
# When these appear in the error message we stop immediately rather than retrying.
QUOTA_EXHAUSTION_PHRASES = [
    "quota exceeded",
    "daily quota",
    "resource_exhausted",
    "quota_exceeded",
    "generativelanguage.googleapis.com",   # free-tier resource URL fragment
]

# Required fields every checkpoint record must contain.
REQUIRED_FIELDS = {
    "question_id", "question", "category",
    "answer", "api_failure", "error_category",
    "model_used", "retrieved_chunk_ids", "retrieved_sources",
    "latency_s", "is_refusal",
}

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint(path: Path) -> tuple[dict[str, dict], list[str]]:
    """
    Reads the JSONL checkpoint file.

    Returns
    -------
    completed : dict[question_id -> record]
        Records that have a *successful* answer (api_failure=False).
        These will be SKIPPED on this run.
    warnings : list[str]
        Non-fatal issues found (malformed lines, missing fields, etc.).
    """
    completed: dict[str, dict] = {}
    warnings: list[str] = []

    if not path.exists():
        return completed, warnings

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, raw in enumerate(raw_lines, 1):
        raw = raw.strip()
        if not raw:
            continue

        # Parse JSON
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as exc:
            warnings.append(f"Line {lineno}: malformed JSON — {exc}. Line skipped.")
            continue

        # Validate required fields
        if not isinstance(rec, dict):
            warnings.append(f"Line {lineno}: record is not a JSON object. Line skipped.")
            continue
        missing = REQUIRED_FIELDS - rec.keys()
        if missing:
            warnings.append(
                f"Line {lineno}: record for qid={rec.get('question_id','?')} "
                f"missing fields {missing}. Line skipped."
            )
            continue

        qid = rec["question_id"]
        if not isinstance(qid, str) or not qid.startswith("Q"):
            warnings.append(f"Line {lineno}: invalid question_id '{qid}'. Line skipped.")
            continue

        # Only count records with a successful answer as 'completed'.
        # API failures are intentionally retried on the next run.
        if not rec["api_failure"]:
            # Keep the most recent successful record if there are duplicates.
            completed[qid] = rec
        else:
            # Failure is logged for diagnostics but not in 'completed'.
            warnings.append(
                f"  [CHECKPOINT] {qid}: previous run returned api_failure=True "
                f"(error_category={rec.get('error_category','?')}). Will retry."
            )

    return completed, warnings


def append_checkpoint(path: Path, record: dict) -> None:
    """Appends one JSONL record and closes the file immediately."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Local Gemini wrapper (does not modify backend/qa_service.py)
# ---------------------------------------------------------------------------

def ask_gemini_eval(
    prompt: str,
    system_prompt: str,
) -> tuple[Optional[str], str, str]:
    """
    Calls the Gemini API, trying each model in EVAL_MODELS with bounded retries.

    Returns
    -------
    answer       : str or None   (None means API failure)
    model_used   : str           (model name that succeeded, or last tried, or "none")
    error_category : str         ("none" | "transient" | "quota_exhausted" | "unknown")
    """
    # Import here so syntax checks work without needing the package installed.
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BACKEND / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. Ensure backend/.env contains GEMINI_API_KEY=<key>"
        )
    # Key is never stored, returned, or printed.

    from google import genai
    from google.genai import types, errors

    client = genai.Client(api_key=api_key)

    last_model = "none"
    for model_name in EVAL_MODELS:
        last_model = model_name
        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.0,
                    ),
                )
                if response.text:
                    return response.text, model_name, "none"
                # Empty response body — treat as transient and move to next model.
                break

            except errors.APIError as exc:
                err_msg = str(exc).lower()
                is_quota = any(phrase in err_msg for phrase in QUOTA_EXHAUSTION_PHRASES)

                if is_quota:
                    # Daily quota: retrying the same or different model is futile.
                    print(f"    [QUOTA] {model_name} attempt {attempt+1}: quota exhausted — stopping.")
                    return None, model_name, "quota_exhausted"

                if exc.code in (429, 500, 503, 504):
                    # Transient error: back off and retry.
                    print(f"    [TRANSIENT] {model_name} attempt {attempt+1}: {exc.code}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(BACKOFF_BASE ** attempt)
                    continue

                # Non-retryable client error (4xx other than 429).
                print(f"    [ERROR] {model_name}: {exc.code} — {exc}")
                break

            except Exception as exc:
                print(f"    [UNEXPECTED] {model_name} attempt {attempt+1}: {exc}")
                break

    return None, last_model, "transient"


# ---------------------------------------------------------------------------
# PDF / index helpers (unchanged from original)
# ---------------------------------------------------------------------------

def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def build_index(pdfs: list[Path]) -> list[dict]:
    """Re-builds a fresh FAISS index from the PDFs and returns metadata list."""
    import faiss

    all_chunks, meta = [], []
    for pdf in pdfs:
        text = extract_pdf(pdf)
        if len(text) < 50:
            raise SystemExit(f"Too little text in {pdf.name}")
        for i, chunk in enumerate(chunk_text(text, size=1000, overlap=200)):
            all_chunks.append(chunk)
            meta.append({"chunk_id": f"{pdf.stem}_c{i:03d}", "source": pdf.name, "chunk": chunk})

    embeddings = embed_model.encode(all_chunks, show_progress_bar=True)

    vector_store.index = faiss.IndexFlatL2(384)
    vector_store.stored_chunks = []
    vector_store.add_to_index(embeddings, all_chunks)

    print(f"Index built: {len(pdfs)} PDFs, {len(all_chunks)} chunks")
    return meta


def retrieve(question: str, meta: list[dict], k: int = K_RETRIEVAL) -> list[dict]:
    qv = embed_model.encode([question])[0]
    hit_chunks = vector_store.search(qv, k=k)
    chunk_to_meta = {m["chunk"]: m for m in meta}
    return [
        chunk_to_meta.get(c, {"chunk_id": "UNKNOWN", "source": "UNKNOWN", "chunk": c})
        for c in hit_chunks
    ]


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n---\n\n".join(c["chunk"] for c in chunks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def is_refusal(answer: Optional[str]) -> bool:
    return bool(answer) and REFUSAL_PHRASE.lower() in answer.lower()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    "If the answer is not in the context, reply exactly: "
    "'I could not find this in the document.' "
    "Do not use outside knowledge and do not guess."
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(DOCS.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(
            f"No PDFs found in {DOCS}. "
            "Copy Dsa.pdf, spring_boot_tutorial.pdf, css.pdf there."
        )

    questions = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
    print(f"Questions loaded: {len(questions)}")

    # --- Load checkpoint ---
    completed, ckpt_warnings = load_checkpoint(CHECKPOINT_FILE)
    if ckpt_warnings:
        print(f"\n[CHECKPOINT] {len(ckpt_warnings)} warning(s):")
        for w in ckpt_warnings:
            print(f"  {w}")
    if completed:
        print(f"[CHECKPOINT] {len(completed)} question(s) already answered — will skip.")
    print()

    # --- Build index (needed even for pure resume runs to decode retrieval) ---
    meta = build_index(pdfs)

    # Start per_question with already-completed records so final aggregation is correct.
    per_question: list[dict] = list(completed.values())
    new_answers = 0
    new_failures = 0
    skipped_completed = len(completed)
    quota_stop = False

    # --- Question loop ---
    for q in questions:
        qid = q["question_id"]

        if qid in completed:
            print(f"  [SKIP] {qid}: already answered (loaded from checkpoint)")
            continue

        if quota_stop:
            print(f"  [QUOTA-STOP] {qid}: skipping — quota exhausted earlier this run")
            continue

        question_text = q["question"]
        scope = q["source_scope"]

        retrieved = retrieve(question_text, meta, k=K_RETRIEVAL)
        prompt = build_prompt(question_text, retrieved)

        t_start = time.perf_counter()
        answer, model_used, error_category = ask_gemini_eval(prompt, SYSTEM_PROMPT)
        latency_s = round(time.perf_counter() - t_start, 3)

        api_failure = (answer is None)
        refusal = is_refusal(answer)

        record = {
            "question_id": qid,
            "category": scope,
            "question": question_text,
            "reference_answer": q["reference_answer"],
            "retrieved_chunk_ids": [r["chunk_id"] for r in retrieved],
            "retrieved_sources": [r["source"] for r in retrieved],
            "answer": answer,
            "is_refusal": refusal,
            "api_failure": api_failure,
            "error_category": error_category,
            "model_used": model_used,
            "latency_s": latency_s,
        }
        per_question.append(record)

        # Checkpoint: append immediately, close after write.
        # Both successes AND failures are checkpointed for diagnostics,
        # but only successes are treated as 'completed' on the next load.
        append_checkpoint(CHECKPOINT_FILE, record)

        if api_failure:
            new_failures += 1
            print(f"  [FAIL] {qid}: {error_category} via {model_used}")
            if error_category == "quota_exhausted":
                quota_stop = True
                print("  [QUOTA-STOP] Daily quota exhausted — halting API calls for this run.")
        elif refusal:
            new_answers += 1          # counts as answered (model processed it)
            print(f"  [REFUSAL] {qid}: model refused (model={model_used})")
        else:
            new_answers += 1
            preview = (answer or "")[:80].replace("\n", " ")
            print(f"  [OK] {qid}: {preview}  (model={model_used}, {latency_s}s)")

        if not quota_stop:
            time.sleep(INTER_REQUEST_SLEEP)

    # --- Final aggregation (writes raw JSON and summary CSV) ---
    _write_outputs(per_question, pdfs, meta, skipped_completed, quota_stop)

    # --- Print run summary ---
    total = len(per_question)
    answered = sum(1 for r in per_question if not r["api_failure"] and not r["is_refusal"])
    refused = sum(1 for r in per_question if r["is_refusal"])
    failed = sum(1 for r in per_question if r["api_failure"])
    quota_failed = sum(1 for r in per_question if r.get("error_category") == "quota_exhausted")

    print("\n" + "=" * 60)
    print("Answer Quality Run Summary")
    print(f"  Total questions processed : {total}")
    print(f"  Answered (model output)   : {answered}")
    print(f"  Refusals                  : {refused}")
    print(f"  API failures (all kinds)  : {failed}")
    print(f"    of which quota-exhausted: {quota_failed}")
    print(f"  Resumed from checkpoint   : {skipped_completed}")
    print(f"  New answers this run      : {new_answers}")
    if quota_stop:
        unanswered = sum(1 for q in questions
                         if q["question_id"] not in {r["question_id"] for r in per_question})
        print(f"  Unanswered (quota stop)   : {unanswered}")
        print()
        print("  ACTION: Wait for daily quota reset, then re-run this script.")
        print("  Completed results are safe in the checkpoint file.")
    valid_latencies = [r["latency_s"] for r in per_question if not r["api_failure"]]
    if valid_latencies:
        avg_lat = sum(valid_latencies) / len(valid_latencies)
        print(f"  Avg latency (answered)    : {avg_lat:.2f}s  [API latency is variable]")
    print("=" * 60)
    print("WARNING: Answers have not been verified for factual correctness.")
    print("Use answer_quality_raw.json for manual adjudication before paper reporting.")


def _write_outputs(
    per_question: list[dict],
    pdfs: list[Path],
    meta: list[dict],
    skipped_completed: int,
    quota_stop: bool,
) -> None:
    """Writes final answer_quality_raw.json and answer_quality_summary.csv."""

    # Separate records clearly in the output.
    successes = [r for r in per_question if not r["api_failure"] and not r["is_refusal"]]
    refusals = [r for r in per_question if r["is_refusal"]]
    failures = [r for r in per_question if r["api_failure"]]

    raw_out = OUT / "answer_quality_raw.json"
    raw_out.write_text(
        json.dumps(
            {
                "metadata": {
                    "pdfs": [p.name for p in pdfs],
                    "chunk_count": len(meta),
                    "question_count_in_bank": 30,
                    "k_retrieval": K_RETRIEVAL,
                    "resumed_from_checkpoint": skipped_completed,
                    "quota_stop_triggered": quota_stop,
                    "warning": (
                        "Answers are generated by Gemini conditioned on retrieved context. "
                        "Semantic similarity to reference answers is NOT verified factual correctness. "
                        "Manual review is required before paper reporting. "
                        "api_failure=True records contain NO generated answer."
                    ),
                },
                "answered": successes,
                "refusals": refusals,
                "api_failures": failures,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nRaw results saved: {raw_out}")

    summary_out = OUT / "answer_quality_summary.csv"
    fieldnames = [
        "question_id", "category", "question", "reference_answer",
        "model_used", "retrieved_sources",
        "answer", "is_refusal", "api_failure", "error_category", "latency_s",
    ]
    with summary_out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in per_question:
            row = {k: r.get(k, "") for k in fieldnames if k != "retrieved_sources"}
            row["retrieved_sources"] = " | ".join(r.get("retrieved_sources", []))
            writer.writerow(row)
    print(f"Summary CSV saved: {summary_out}")


if __name__ == "__main__":
    main()
