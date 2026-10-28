"""
test_checkpoint_logic.py
Tests the checkpoint load/save/resume logic in run_real_pdf_answer_quality.py.
Makes ZERO Gemini API calls -- all API calls are mocked.

Run from project root:
    python evaluation/runners/test_checkpoint_logic.py
"""
import json
import sys
import tempfile
import os
from pathlib import Path

# Point at the runner's own directory so we can import its helpers.
RUNNER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUNNER_DIR))

# -- Patch heavy imports before importing the runner --------------------------
import types as _types

for mod_name in [
    "google", "google.genai", "google.genai.types", "google.genai.errors",
    "faiss", "sentence_transformers",
]:
    sys.modules.setdefault(mod_name, _types.ModuleType(mod_name))

# PyPDF2 needs a PdfReader attribute at the class level.
_pypdf2 = _types.ModuleType("PyPDF2")
_pypdf2.PdfReader = type("PdfReader", (), {})
sys.modules["PyPDF2"] = _pypdf2

# Stub out backend modules the runner imports at module level.
for mod_name in ["chunking", "embeddings", "vector_store", "qa_service"]:
    sys.modules[mod_name] = _types.ModuleType(mod_name)

sys.modules["embeddings"].model = None
sys.modules["vector_store"].index = None
sys.modules["vector_store"].stored_chunks = []
sys.modules["vector_store"].add_to_index = lambda *a, **kw: None
sys.modules["vector_store"].search = lambda *a, **kw: []
sys.modules["chunking"].chunk_text = lambda text, size=1000, overlap=200: [text]
sys.modules["qa_service"].ask_gemini = lambda *a, **kw: None

os.environ.setdefault("GEMINI_API_KEY", "TEST_KEY_NOT_REAL")

# Import only helpers -- no main(), no API.
from run_real_pdf_answer_quality import (
    load_checkpoint, append_checkpoint, is_refusal, REQUIRED_FIELDS,
)

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(name: str, condition: bool, detail: str = "") -> None:
    tag = PASS if condition else FAIL
    print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
    results.append(condition)


print("=" * 60)
print("Checkpoint / Resume Logic -- Local Mock Tests")
print("No Gemini API calls are made in this test.")
print("=" * 60)

# Minimal valid record template.
GOOD_REC = {
    "question_id": "Q01", "category": "DSA", "question": "What is X?",
    "reference_answer": "X is Y", "retrieved_chunk_ids": ["Dsa_c000"],
    "retrieved_sources": ["Dsa.pdf"], "answer": "X is Y",
    "is_refusal": False, "api_failure": False,
    "error_category": "none", "model_used": "gemini-2.0-flash", "latency_s": 1.2,
}

with tempfile.TemporaryDirectory() as tmp:
    ckpt = Path(tmp) / "checkpoint.jsonl"

    # TEST 1: Empty / missing file
    print("\n[1] Empty checkpoint file")
    completed, warns = load_checkpoint(ckpt)
    check("Returns empty dict for missing file", completed == {})
    check("No warnings for missing file", warns == [])

    # TEST 2: Single successful record
    print("\n[2] Single successful record")
    append_checkpoint(ckpt, GOOD_REC)
    completed, warns = load_checkpoint(ckpt)
    check("Successful record is in completed", "Q01" in completed)
    check("No warnings for valid record", len(warns) == 0)
    check("Required fields preserved", set(completed["Q01"].keys()) >= REQUIRED_FIELDS)

    # TEST 3: API failure record -- must NOT be in completed
    print("\n[3] API failure (transient) -- not in completed, retryable")
    fail_rec = {**GOOD_REC, "question_id": "Q02", "answer": None,
                "api_failure": True, "error_category": "transient", "model_used": "gemini-2.0-flash"}
    append_checkpoint(ckpt, fail_rec)
    completed, warns = load_checkpoint(ckpt)
    check("Q01 still in completed", "Q01" in completed)
    check("Q02 (transient fail) NOT in completed", "Q02" not in completed)
    check("Warning emitted for Q02 failure", any("Q02" in w for w in warns))

    # TEST 4: Quota-exhausted failure -- also not in completed
    print("\n[4] Quota-exhausted failure -- not in completed, retryable")
    quota_rec = {**GOOD_REC, "question_id": "Q03", "answer": None,
                 "api_failure": True, "error_category": "quota_exhausted", "model_used": "gemini-2.0-flash"}
    append_checkpoint(ckpt, quota_rec)
    completed, warns = load_checkpoint(ckpt)
    check("Q03 (quota fail) NOT in completed", "Q03" not in completed)
    check("Quota fail warning emitted", any("Q03" in w for w in warns))

    # TEST 5: Malformed JSON line -- skip with warning, preserve valid records
    print("\n[5] Malformed JSONL line")
    ckpt2 = Path(tmp) / "checkpoint2.jsonl"
    ckpt2.write_text(
        json.dumps(GOOD_REC) + "\n"
        + "THIS IS NOT JSON\n"
        + json.dumps({**GOOD_REC, "question_id": "Q04"}) + "\n",
        encoding="utf-8",
    )
    completed2, warns2 = load_checkpoint(ckpt2)
    check("Q01 loaded despite bad line", "Q01" in completed2)
    check("Q04 loaded despite bad line", "Q04" in completed2)
    check("Warning issued for malformed line", any("malformed" in w.lower() for w in warns2))
    check("Only bad line skipped (2 good records)", len(completed2) == 2)

    # TEST 6: Record missing required fields
    print("\n[6] Record missing required fields")
    ckpt3 = Path(tmp) / "checkpoint3.jsonl"
    bad_rec = {"question_id": "Q05", "answer": "something"}
    ckpt3.write_text(json.dumps(bad_rec) + "\n", encoding="utf-8")
    completed3, warns3 = load_checkpoint(ckpt3)
    check("Incomplete record NOT in completed", "Q05" not in completed3)
    check("Warning issued for missing fields", any("missing fields" in w for w in warns3))

    # TEST 7: Duplicate records -- latest successful wins
    print("\n[7] Duplicate successful records -- latest survives")
    ckpt4 = Path(tmp) / "checkpoint4.jsonl"
    rec_v1 = {**GOOD_REC, "answer": "First answer", "latency_s": 1.0}
    rec_v2 = {**GOOD_REC, "answer": "Second answer", "latency_s": 2.0}
    ckpt4.write_text(
        json.dumps(rec_v1) + "\n" + json.dumps(rec_v2) + "\n",
        encoding="utf-8",
    )
    completed4, _ = load_checkpoint(ckpt4)
    check("Latest record survives dedup", completed4["Q01"]["answer"] == "Second answer")

    # TEST 8: is_refusal helper
    print("\n[8] is_refusal helper")
    check("Exact phrase detected",
          is_refusal("I could not find this in the document."))
    check("Phrase inside longer answer detected",
          is_refusal("Sorry. I could not find this in the document. Please try."))
    check("None answer is not a refusal", not is_refusal(None))
    check("Unrelated answer is not a refusal", not is_refusal("The answer is X."))
    check("Case-insensitive match",
          is_refusal("i COULD NOT FIND this in the document."))

    # TEST 9: append_checkpoint flushes and closes after each write
    print("\n[9] append_checkpoint flushes and closes after each write")
    ckpt5 = Path(tmp) / "checkpoint5.jsonl"
    for i in range(3):
        r = {**GOOD_REC, "question_id": f"Q{i+10:02d}"}
        append_checkpoint(ckpt5, r)
    lines = [l for l in ckpt5.read_text(encoding="utf-8").splitlines() if l.strip()]
    check("3 records written, each on its own line", len(lines) == 3)
    parsed = [json.loads(l) for l in lines]
    check("Q10, Q11, Q12 all present",
          {p["question_id"] for p in parsed} == {"Q10", "Q11", "Q12"})

    # TEST 10: Resume skips completed, retries failures
    print("\n[10] Resume: skipped qids derive correctly from completed dict")
    ckpt6 = Path(tmp) / "checkpoint6.jsonl"
    for qid, is_fail in [("Q01", False), ("Q02", True), ("Q03", False)]:
        r = {**GOOD_REC, "question_id": qid,
             "answer": None if is_fail else "Some answer",
             "api_failure": is_fail,
             "error_category": "transient" if is_fail else "none"}
        append_checkpoint(ckpt6, r)
    completed6, _ = load_checkpoint(ckpt6)
    check("Only Q01 and Q03 (successes) in completed", set(completed6.keys()) == {"Q01", "Q03"})
    check("Q02 (failure) excluded from completed -- will be retried", "Q02" not in completed6)

print()
passed = sum(results)
total = len(results)
print("=" * 60)
print(f"Results: {passed}/{total} tests passed")
if passed == total:
    print("ALL TESTS PASSED. No Gemini API calls were made.")
else:
    failed_n = [i+1 for i, r in enumerate(results) if not r]
    print(f"FAILED check numbers: {failed_n}")
print("=" * 60)
sys.exit(0 if passed == total else 1)
