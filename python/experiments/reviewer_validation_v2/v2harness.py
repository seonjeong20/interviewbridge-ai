"""Bootstraps the v1 harness for the v2 experiments.

The v1 harness (../reviewer_validation/harness.py) is reused unmodified for
running production stages, cost accounting and the LLM judges. Only its output
locations are redirected so that nothing under the v1 results directory is
ever written.
"""

import json
import sys
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent
V1_DIR = V2_DIR.parent / "reviewer_validation"
V1_RESULTS = V1_DIR / "results"

sys.path.insert(0, str(V1_DIR))

import harness as h  # noqa: E402

h.RESULTS_DIR = V2_DIR / "results"
h.RESULTS_DIR.mkdir(exist_ok=True)
h.LEDGER = h.RESULTS_DIR / "call_ledger.jsonl"


def load_cases():
    return json.loads((V1_DIR / "test_cases.json").read_text())["cases"]


def load_v1(name):
    return json.loads((V1_RESULTS / name).read_text())


def evaluator_raw(case):
    """The exact string v1 fed to the Reviewer and the Coach for this case."""
    return json.dumps(case["evaluator_output"], ensure_ascii=False, indent=2)
