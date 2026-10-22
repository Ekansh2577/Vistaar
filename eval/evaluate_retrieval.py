"""
VISTAAR Retrieval Accuracy Evaluation Benchmark
Compares Top-K retrieval configurations (K=3, K=5, K=8 [current default], K=10)
on a representative knowledge corpus without modifying backend code.
"""

import sys
from pathlib import Path

# Add backend directory to path to use exact backend modules
BACKEND_DIR = Path(r"C:\Users\ekans\OneDrive\New folder\vis\Vistaar-main\backend")
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import faiss
from chunking import chunk_text
from embeddings import get_embeddings, model

# Representative technical document simulating typical VISTAAR user upload
SAMPLE_DOCUMENT = """
# VISTAAR System Architecture and Knowledge Retrieval Specification

## 1. Introduction and Objectives
VISTAAR is an enterprise-grade document intelligence platform designed to ground large language models
in authoritative private knowledge assets. By coupling dense vector search with large generative models,
VISTAAR prevents hallucinations, ensures data provenance, and provides verifiable citations for technical teams.

## 2. Ingestion and Preprocessing Pipeline
When a user uploads a document (PDF or TXT format), the ingestion module reads raw binary streams.
PDF documents are parsed using PyPDF2, extracting page-by-page text. If extracted text is under 50 characters,
the ingestion engine rejects the file with an unreadable document error.
Valid documents enter a sliding-window chunker configured with a chunk size of 1000 characters and an overlap
of 200 characters. This ensures semantic continuity across chunk boundaries without losing context between sections.

## 3. Embedding Generation and Representation
Text chunks are transformed into 384-dimensional dense semantic vectors using the all-MiniLM-L6-v2 model.
The sentence-transformer model operates locally on CPU or GPU, executing normalized vector projections.
Embeddings capture latent semantic associations, enabling synonym matching and conceptual retrieval
that outperforms traditional lexical BM25 matching for complex paraphrased queries.

## 4. Vector Storage and Similarity Indexing
Embeddings are indexed into an in-memory FAISS IndexFlatL2 index. FAISS IndexFlatL2 executes exact
Euclidean distance (L2) nearest neighbor queries across the 384-dimensional vector space.
The index does not apply lossy clustering or Voronoi partitioning (IVF), ensuring 100% search recall
at the expense of linear scan overhead during query time.
Chunks are stored sequentially in an in-memory list synchronized with FAISS vector offsets.

## 5. Query Processing and Context Assembly
When a user submits a natural language question via POST /ask, the query is encoded using the identical
all-MiniLM-L6-v2 embedding model. The resulting 384-dimensional vector queries the FAISS index to retrieve
top-K nearest chunks. The retrieved chunks are concatenated with separator tokens ('\\n\\n---\\n\\n')
and embedded into a strictly constrained prompt template.

## 6. Rate Limiting and Production Constraints
To protect upstream inference APIs and ensure system availability, VISTAAR implements SlowAPI rate limiters:
Document uploads are throttled to a maximum of 5 requests per minute per IP address.
Question answering requests are throttled to 10 requests per minute per IP address.
Exceeding these thresholds triggers an HTTP 429 RateLimitExceeded response.

## 7. Generative Grounding and Strict Context Constraints
The prompt is dispatched to Gemini with a temperature parameter of 0.0. The system instruction strictly
mandates that if an answer cannot be deduced entirely from the retrieved context chunks, the model must
reply exactly: 'I could not find this in the document.' No external parametric knowledge or guessing is permitted.
"""

# Ground-truth test queries with expected relevant section keywords
TEST_CASES = [
    {
        "id": "Q1_Specific_Fact",
        "question": "What is the exact chunk size and overlap used by the chunker?",
        "target_keywords": ["1000 characters", "overlap of 200 characters"],
        "expected_answer": "Chunk size of 1000 characters and an overlap of 200 characters.",
        "difficulty": "direct_factoid"
    },
    {
        "id": "Q2_Technical_Spec",
        "question": "What embedding model and vector dimension are used?",
        "target_keywords": ["all-MiniLM-L6-v2", "384-dimensional"],
        "expected_answer": "all-MiniLM-L6-v2 model with 384-dimensional dense vectors.",
        "difficulty": "direct_factoid"
    },
    {
        "id": "Q3_Rate_Limits",
        "question": "What are the rate limits for document upload and asking questions?",
        "target_keywords": ["5 requests per minute", "10 requests per minute", "SlowAPI"],
        "expected_answer": "Upload: 5/min, Ask: 10/min via SlowAPI.",
        "difficulty": "multi_factoid"
    },
    {
        "id": "Q4_Negative_Test",
        "question": "What is the maximum allowed file size for video uploads in megabytes?",
        "target_keywords": ["video uploads"],
        "expected_answer": "I could not find this in the document. (Video not supported)",
        "difficulty": "unanswerable_negative"
    },
]

def run_evaluation():
    print("=" * 60)
    print("VISTAAR RETRIEVAL ACCURACY & K PARAMETER BENCHMARK")
    print("=" * 60)

    # 1. Chunk document
    chunks = chunk_text(SAMPLE_DOCUMENT, size=1000, overlap=200)
    print(f"Total Document Length: {len(SAMPLE_DOCUMENT)} chars")
    print(f"Generated Chunks: {len(chunks)} chunks (size=1000, overlap=200)")

    # 2. Compute embeddings
    embeddings = get_embeddings(chunks)
    embeddings = np.array(embeddings).astype("float32")

    # 3. Build FAISS index
    dimension = 384
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Values of K to compare
    k_candidates = [3, 5, 8, 10]
    results_by_k = {k: {"hits": 0, "total_chunks": 0, "noise_chunks": 0, "avg_chars": 0, "queries_evaluated": 0} for k in k_candidates}

    print("\n--- Evaluating Queries across K candidates ---")

    for test in TEST_CASES:
        q = test["question"]
        q_vec = model.encode([q]).astype("float32")
        print(f"\nQuery [{test['id']}]: '{q}'")

        for k in k_candidates:
            D, I = index.search(q_vec, k)
            retrieved = [chunks[i] for i in I[0] if 0 <= i < len(chunks)]
            total_chars = sum(len(c) for c in retrieved)

            # Check if relevant keywords appear in any retrieved chunk (with normalized whitespace)
            import re
            if test["difficulty"] == "unanswerable_negative":
                # For negative test, all chunks are technically distractors
                hits = 0
                noise = len(retrieved)
            else:
                hit_count = 0
                for c in retrieved:
                    c_norm = re.sub(r'\s+', ' ', c.lower())
                    if all(re.sub(r'\s+', ' ', kw.lower()) in c_norm for kw in test["target_keywords"]):
                        hit_count += 1
                hits = 1 if hit_count > 0 else 0
                noise = len(retrieved) - hit_count

            results_by_k[k]["hits"] += hits
            results_by_k[k]["total_chunks"] += len(retrieved)
            results_by_k[k]["noise_chunks"] += noise
            results_by_k[k]["avg_chars"] += total_chars
            results_by_k[k]["queries_evaluated"] += 1

            status = "HIT" if hits > 0 or test["difficulty"] == "unanswerable_negative" else "MISS"
            print(f"  K={k:2d}: {status} | Retrieved: {len(retrieved)} chunks ({total_chars} chars) | Distractor chunks: {noise}")

    print("\n" + "=" * 60)
    print("AGGREGATE BENCHMARK RESULTS")
    print("=" * 60)
    print(f"{'K':<5} | {'Recall@K (Ans.)':<16} | {'Noise Ratio':<14} | {'Avg Context Chars':<18} | {'Est. Prompt Tokens':<18}")
    print("-" * 75)

    positive_queries = sum(1 for t in TEST_CASES if t["difficulty"] != "unanswerable_negative")

    for k in k_candidates:
        recall = (results_by_k[k]["hits"] / positive_queries) * 100
        noise_ratio = (results_by_k[k]["noise_chunks"] / results_by_k[k]["total_chunks"]) * 100
        avg_chars = results_by_k[k]["avg_chars"] / len(TEST_CASES)
        est_tokens = int(avg_chars / 4)

        current_marker = " (Current Default)" if k == 8 else ""
        print(f"K={k:<3} | {recall:5.1f}%          | {noise_ratio:5.1f}%        | {avg_chars:7.0f} chars      | ~{est_tokens:<6} tokens{current_marker}")

    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()
