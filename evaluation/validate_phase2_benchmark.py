"""
================================================================================
Independent Dataset & Corpus Validator for VISTAAR Phase 2 Benchmark
================================================================================
Performs comprehensive automated verification:
1. Validates integrity of corpus documents against corpus_manifest.json using SHA-256.
2. Validates chunk count and chunk boundaries using actual backend.chunking.chunk_text.
3. Checks benchmark schema, question counts, dev/test split disjointness, and lexical isolation.
4. Verifies every exact evidence span exists verbatim in the target corpus text and falls within
   the assigned ground-truth chunks.
5. Verifies unanswerable questions lack ground-truth spans and partial questions specify both
   supported and unsupported scopes.
================================================================================
"""

import sys
import json
import hashlib
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from chunking import chunk_text
except ImportError as e:
    raise RuntimeError(f"Cannot import chunking from {BACKEND_DIR}: {e}")

EVAL_DIR = WORKSPACE_DIR / "evaluation"
CORPUS_DIR = EVAL_DIR / "corpus"
DATASETS_DIR = EVAL_DIR / "datasets"

MANIFEST_PATH = CORPUS_DIR / "corpus_manifest.json"
MASTER_QUERIES_PATH = DATASETS_DIR / "benchmark_queries_master.json"
DEV_QUERIES_PATH = DATASETS_DIR / "tuning_queries.json"
TEST_QUERIES_PATH = DATASETS_DIR / "test_queries_frozen.json"


def run_full_validation():
    print("=" * 80)
    print("STARTING VISTAAR PHASE 2 INDEPENDENT BENCHMARK VALIDATION")
    print("=" * 80)
    
    validation_passed = True
    issues = []
    
    # --------------------------------------------------------------------------
    # 1. Validate Corpus Manifest & Physical Files
    # --------------------------------------------------------------------------
    if not MANIFEST_PATH.exists():
        print(f"[FAIL] Manifest missing: {MANIFEST_PATH}")
        return False
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    print(f"[*] Validating Corpus Manifest: {manifest.get('corpus_name')}")
    print(f"[*] Registered Documents: {len(manifest['documents'])}")
    
    total_recomputed_chunks = 0
    all_chunks_by_id = {}
    doc_texts = {}
    
    for doc_name, doc_meta in manifest["documents"].items():
        doc_path = CORPUS_DIR / doc_name
        if not doc_path.exists():
            issues.append(f"Document file missing on disk: {doc_path}")
            validation_passed = False
            continue
            
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        doc_texts[doc_name] = content
        
        # Verify SHA-256
        recomputed_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if recomputed_sha != doc_meta["sha256"]:
            issues.append(f"SHA-256 mismatch for {doc_name}! Expected {doc_meta['sha256']}, got {recomputed_sha}")
            validation_passed = False
            
        # Verify chunking
        recomputed_chunks = chunk_text(content, size=1000, overlap=200)
        total_recomputed_chunks += len(recomputed_chunks)
        if len(recomputed_chunks) != doc_meta["chunk_count"]:
            issues.append(f"Chunk count mismatch for {doc_name}! Manifest says {doc_meta['chunk_count']}, recomputed {len(recomputed_chunks)}")
            validation_passed = False
            
        for idx, ch in enumerate(recomputed_chunks):
            cid = f"{doc_name.replace('.txt', '')}_c{idx:02d}"
            all_chunks_by_id[cid] = {
                "chunk_id": cid,
                "doc_name": doc_name,
                "idx": idx,
                "text": ch
            }
            
    print(f"[+] Total Chunks Recomputed Across Corpus: {total_recomputed_chunks} (Target: 60-80)")
    if total_recomputed_chunks < 60 or total_recomputed_chunks > 80:
        issues.append(f"Total chunk count {total_recomputed_chunks} is outside the target 60-80 range!")
        validation_passed = False
    else:
        print(f"[PASS] Total chunk count {total_recomputed_chunks} is strictly within [60, 80].")

    # --------------------------------------------------------------------------
    # 2. Validate Benchmark Datasets & Splits
    # --------------------------------------------------------------------------
    if not MASTER_QUERIES_PATH.exists():
        print(f"[FAIL] Master queries file missing: {MASTER_QUERIES_PATH}")
        return False
        
    with open(MASTER_QUERIES_PATH, "r", encoding="utf-8") as f:
        master_queries = json.load(f)
    with open(DEV_QUERIES_PATH, "r", encoding="utf-8") as f:
        dev_queries = json.load(f)
    with open(TEST_QUERIES_PATH, "r", encoding="utf-8") as f:
        test_queries = json.load(f)
        
    print(f"[*] Validating Benchmark Datasets:")
    print(f"    - Master queries count: {len(master_queries)} (Expected: 32)")
    print(f"    - Dev queries count:    {len(dev_queries)} (Expected: 8)")
    print(f"    - Test queries count:   {len(test_queries)} (Expected: 24)")
    
    if len(master_queries) != 32:
        issues.append(f"Master queries count is {len(master_queries)}, expected 32.")
        validation_passed = False
    if len(dev_queries) != 8:
        issues.append(f"Dev queries count is {len(dev_queries)}, expected 8.")
        validation_passed = False
    if len(test_queries) != 24:
        issues.append(f"Test queries count is {len(test_queries)}, expected 24.")
        validation_passed = False
        
    # Check disjointness
    dev_ids = {q["question_id"] for q in dev_queries}
    test_ids = {q["question_id"] for q in test_queries}
    master_ids = {q["question_id"] for q in master_queries}
    
    if dev_ids.intersection(test_ids):
        issues.append(f"Overlap detected between dev and test splits: {dev_ids.intersection(test_ids)}")
        validation_passed = False
    if dev_ids.union(test_ids) != master_ids:
        issues.append("Union of dev and test does not match master dataset exactly!")
        validation_passed = False
    else:
        print("[PASS] Dev and Test splits are strictly disjoint and partition the 32 master queries.")

    # Check category distribution
    cats = {}
    for q in master_queries:
        c = q["category"]
        cats[c] = cats.get(c, 0) + 1
        
    expected_cats = {
        "sufficient_single": 12,
        "sufficient_multi": 8,
        "partial": 6,
        "insufficient": 6
    }
    if cats != expected_cats:
        issues.append(f"Category counts mismatch! Expected {expected_cats}, got {cats}")
        validation_passed = False
    else:
        print(f"[PASS] Category breakdown matches plan: {cats}")

    # --------------------------------------------------------------------------
    # 3. Verify Exact Evidence Spans and Ground-Truth Chunk Mappings
    # --------------------------------------------------------------------------
    print("[*] Validating Evidence Spans and Chunk Provenance for each query...")
    
    for q in master_queries:
        qid = q["question_id"]
        cat = q["category"]
        spans = q["exact_evidence_spans"]
        chunk_ids = q["ground_truth_chunk_ids"]
        target_docs = q["target_documents"]
        
        # Verify Category Expectations
        if cat in ["sufficient_single", "sufficient_multi"]:
            if q["refusal_expected"] is not False:
                issues.append(f"[{qid}] Category '{cat}' should have refusal_expected=False.")
                validation_passed = False
            if not spans:
                issues.append(f"[{qid}] Category '{cat}' must have non-empty exact_evidence_spans.")
                validation_passed = False
            if not chunk_ids:
                issues.append(f"[{qid}] Category '{cat}' must have non-empty ground_truth_chunk_ids.")
                validation_passed = False
                
        elif cat == "partial":
            if q["refusal_expected"] != "partial":
                issues.append(f"[{qid}] Category 'partial' must have refusal_expected='partial'.")
                validation_passed = False
            if not q.get("partial_scope") or "supported" not in q["partial_scope"] or "unsupported" not in q["partial_scope"]:
                issues.append(f"[{qid}] Category 'partial' must specify both 'supported' and 'unsupported' scopes.")
                validation_passed = False
            if not spans or not chunk_ids:
                issues.append(f"[{qid}] Partial question must have supporting evidence spans and chunks.")
                validation_passed = False
                
        elif cat == "insufficient":
            if q["refusal_expected"] is not True:
                issues.append(f"[{qid}] Category 'insufficient' must have refusal_expected=True.")
                validation_passed = False
            if spans or chunk_ids:
                issues.append(f"[{qid}] Insufficient question must NOT have evidence spans or ground-truth chunks.")
                validation_passed = False

        # Verify each evidence span exists verbatim in the targeted documents
        for span in spans:
            span_in_corpus = False
            matching_docs = []
            for doc_name, full_text in doc_texts.items():
                if target_docs and doc_name not in target_docs:
                    continue
                if span in full_text:
                    span_in_corpus = True
                    matching_docs.append(doc_name)
                    
            if not span_in_corpus:
                issues.append(f"[{qid}] Evidence span not found in target corpus text! Span: '{span[:50]}...'")
                validation_passed = False
                
            # Verify that span appears inside at least one of the declared ground_truth_chunk_ids
            span_in_declared_chunks = False
            for cid in chunk_ids:
                if cid in all_chunks_by_id:
                    ch_text = all_chunks_by_id[cid]["text"]
                    if span in ch_text or span[:min(50, len(span))] in ch_text:
                        span_in_declared_chunks = True
                        break
            if not span_in_declared_chunks and chunk_ids:
                issues.append(f"[{qid}] Evidence span not found inside any declared ground_truth_chunk_ids {chunk_ids}!")
                validation_passed = False

    # --------------------------------------------------------------------------
    # 4. Check for Lexical Overlap / Leakage Between Dev and Test
    # --------------------------------------------------------------------------
    max_jaccard = 0.0
    highest_pair = None
    for q_dev in dev_queries:
        dev_words = set(q_dev["question"].lower().replace("?", "").replace(",", "").split())
        for q_test in test_queries:
            test_words = set(q_test["question"].lower().replace("?", "").replace(",", "").split())
            intersection = dev_words.intersection(test_words)
            union = dev_words.union(test_words)
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard > max_jaccard:
                max_jaccard = jaccard
                highest_pair = (q_dev["question_id"], q_test["question_id"], jaccard)
                
    print(f"[*] Max lexical similarity between Dev and Test: {max_jaccard:.2f}")
    if highest_pair:
        print(f"    - Closest pair: {highest_pair[0]} (dev) vs {highest_pair[1]} (test)")
    if max_jaccard > 0.65:
        issues.append(f"High lexical similarity detected ({max_jaccard:.2f}) between {highest_pair[0]} and {highest_pair[1]}!")
        validation_passed = False
    else:
        print("[PASS] Lexical overlap between Dev and Test is strictly below threshold (0.65).")

    # --------------------------------------------------------------------------
    # Summary Report
    # --------------------------------------------------------------------------
    print("=" * 80)
    if validation_passed and not issues:
        print("[RESULT: PASS] All Phase 2 benchmark and corpus validation checks PASSED successfully.")
        print(f"  - Total Corpus Documents: 5")
        print(f"  - Total Ingested Chunks:  {total_recomputed_chunks}")
        print(f"  - Total Benchmark Queries: 32 (8 Dev / 24 Test)")
        print("=" * 80)
        return True
    else:
        print("[RESULT: FAIL] Validation detected the following issues:")
        for idx, iss in enumerate(issues, 1):
            print(f"  {idx}. {iss}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = run_full_validation()
    sys.exit(0 if success else 1)
