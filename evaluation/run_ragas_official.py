"""
================================================================================
VISTAAR - Official RAGAS Library Evaluation Runner
================================================================================
Uses the official `ragas` library API to evaluate:
  - Faithfulness
  - Answer Relevancy
  - Context Precision
  - Context Recall

Prerequisites (Isolated Environment):
  pip install -r evaluation/requirements.txt
  Ensure GEMINI_API_KEY is defined in .env
================================================================================
"""

import os
import sys
import json
import csv
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = WORKSPACE_DIR / "backend"
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(WORKSPACE_DIR / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set. Check backend/.env.")

def run_official_ragas():
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    except ImportError as e:
        print(f"\n[!] Official RAGAS dependencies not found: {e}")
        print("    To run with the official RAGAS library, install requirements:")
        print("      pip install -r evaluation/requirements.txt")
        print("\n    Alternatively, run the standalone evaluator without extra dependencies:")
        print("      python evaluation/evaluate_ragas_standalone.py\n")
        return

    input_file = WORKSPACE_DIR / "evaluation" / "results" / "eval_dataset_collected.json"
    results_dir = WORKSPACE_DIR / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        raise FileNotFoundError(f"Dataset not found at {input_file}. Run collect_eval_data.py first.")

    with open(input_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"[*] Preparing HuggingFace Dataset from {len(raw_data)} collected records...")
    formatted_data = {
        "question": [d["user_input"] for d in raw_data],
        "answer": [d["response"] for d in raw_data],
        "contexts": [d["retrieved_contexts"] for d in raw_data],
        "ground_truth": [d["reference"] for d in raw_data],
    }
    dataset = Dataset.from_dict(formatted_data)

    print("[*] Configuring Gemini LLM Judge and Embeddings for RAGAS...")
    eval_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.0
    )
    eval_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    print("[*] Starting RAGAS evaluation execution...")
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=eval_llm,
        embeddings=eval_embeddings,
    )

    df = result.to_pandas()
    official_csv = results_dir / "official_ragas_per_question.csv"
    df.to_csv(official_csv, index=False)
    print(f"[+] Saved official RAGAS metrics to: {official_csv}")
    print("\n" + "=" * 60)
    print("OFFICIAL RAGAS AGGREGATE SCORES:")
    print("=" * 60)
    print(result)

if __name__ == "__main__":
    run_official_ragas()
