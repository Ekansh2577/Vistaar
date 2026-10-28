"""Real-PDF retrieval evaluation for VISTAAR using the project's own embedding/vector modules.

Run from project root after copying the PDFs to evaluation/real_docs/:
  python evaluation/runner/run_real_pdf_vistaar.py

This measures retrieval only. It does not call Gemini or claim answer faithfulness.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DOCS = ROOT / "evaluation" / "real_docs"
OUT = ROOT / "evaluation" / "results" / "real_pdf"
QUESTION_FILE = ROOT / "evaluation" / "real_pdf_question_bank.json"
sys.path.insert(0, str(BACKEND))

from PyPDF2 import PdfReader
from chunking import chunk_text
from embeddings import model
import vector_store


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    questions = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
    pdfs = sorted(DOCS.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {DOCS}. Copy Dsa.pdf, spring_boot_tutorial.pdf, css.pdf there.")

    all_chunks, meta = [], []
    for pdf in pdfs:
        text = extract_pdf(pdf)
        if len(text) < 50:
            raise SystemExit(f"Too little extractable text in {pdf.name}: {len(text)} chars")
        for i, chunk in enumerate(chunk_text(text, size=1000, overlap=200)):
            all_chunks.append(chunk)
            meta.append({"chunk_id": f"{pdf.stem}_c{i:03d}", "source": pdf.name, "chunk": chunk})
    print(f"PDFs={len(pdfs)} chunks={len(all_chunks)} questions={len(questions)}")

    t0 = time.perf_counter()
    embeddings = model.encode(all_chunks, show_progress_bar=True)
    embed_seconds = time.perf_counter() - t0
    # Reset module globals in this fresh process and build the exact FAISS index used by VISTAAR.
    vector_store.index = __import__("faiss").IndexFlatL2(384)
    vector_store.stored_chunks = []
    vector_store.add_to_index(embeddings, all_chunks)

    rows = []
    for q in questions:
        qv = model.encode([q["question"]])[0]
        # Query each requested k using VISTAAR's own search function.
        for k in (3, 5, 8):
            hits = vector_store.search(qv, k=k)
            hit_indices = []
            # Resolve each returned chunk to source metadata in rank order.
            for rank, hit in enumerate(hits, 1):
                idx = next((i for i, m in enumerate(meta) if m["chunk"] == hit), -1)
                hit_indices.append(idx)
                source = meta[idx]["source"] if idx >= 0 else "UNKNOWN"
                chunk_id = meta[idx]["chunk_id"] if idx >= 0 else "UNKNOWN"
                rows.append({
                    "question_id": q["question_id"], "question": q["question"],
                    "scope": q["source_scope"], "k": k, "rank": rank,
                    "expected_answer": q["reference_answer"], "expected_evidence_terms": " | ".join(q["evidence_anchor_terms"]),
                    "retrieved_source": source, "retrieved_chunk_id": chunk_id,
                    "contains_all_anchor_terms": all(term.lower() in hit.lower() for term in q["evidence_anchor_terms"]),
                    "contains_any_anchor_term": any(term.lower() in hit.lower() for term in q["evidence_anchor_terms"]),
                    "retrieved_chunk": hit.replace("\n", " ")
                })
    with (OUT / "real_pdf_retrieval_rankings.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # Summaries are diagnostic only: evidence-anchor string matching is not a full human relevance judgment.
    summary = []
    for k in (3, 5, 8):
        qids = [q["question_id"] for q in questions]
        per_q = []
        for qid in qids:
            rr = [r for r in rows if r["question_id"] == qid and r["k"] == k]
            per_q.append({"qid": qid, "any_anchor": any(r["contains_any_anchor_term"] for r in rr),
                          "all_anchors": any(r["contains_all_anchor_terms"] for r in rr),
                          "expected_source_retrieved": any(r["retrieved_source"] == next(q["source_scope"] for q in questions if q["question_id"] == qid) for r in rr)})
        summary.append({"k": k, "questions": len(qids),
                        "expected_source_hit_rate": sum(x["expected_source_retrieved"] for x in per_q)/len(per_q),
                        "any_anchor_hit_rate": sum(x["any_anchor"] for x in per_q)/len(per_q),
                        "all_anchor_chunk_hit_rate": sum(x["all_anchors"] for x in per_q)/len(per_q),
                        "interpretation": "Diagnostic string-anchor proxy; manually judge evidence before paper reporting."})
    report = {"pdfs": [p.name for p in pdfs], "chunk_count": len(all_chunks), "question_count": len(questions),
              "embedding_seconds": round(embed_seconds, 3), "k_summary": summary,
              "warning": "This runner reports retrieval only. Anchor-string metrics are proxies and must not be described as human-verified precision/recall. Answer quality requires a separate Gemini run and manual adjudication."}
    (OUT / "real_pdf_retrieval_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__": main()
