"""
Mirror copy of evaluation/evaluate_ragas_corrected.py for Phase 1 audit archive.
"""
from pathlib import Path
import sys

EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from evaluate_ragas_corrected import run_corrected_evaluation, WORKSPACE_DIR

if __name__ == "__main__":
    input_data = WORKSPACE_DIR / "evaluation" / "results" / "eval_dataset_collected.json"
    out_dir = WORKSPACE_DIR / "evaluation" / "results" / "audit_v2"
    run_corrected_evaluation(input_data, out_dir)
