"""Improved pipeline on the 51 real Evaluator outputs collected in v1 (exp3).

No Evaluator call is made: the stored outputs are reused, so the production
Reviewer's v1 results on the very same strings are directly comparable.

Usage: python run_natural_outputs.py
"""

import json
import sys

import importlib
import os

import v2harness
import harness as h

VERSION = os.getenv("PIPELINE_VERSION", "v20")
pipeline = importlib.import_module("pipeline_v21" if VERSION == "v21" else "pipeline")
OUT = "e3_natural_runs_v21.json" if VERSION == "v21" else "e3_natural_runs.json"


def main():
    cases = {c["id"]: c for c in v2harness.load_cases()}
    v1 = v2harness.load_v1("exp3_self_consistency.json")
    path = h.RESULTS_DIR / OUT
    runs = json.loads(path.read_text()) if path.exists() else []
    done = {(r["case_id"], r["sample"]) for r in runs}

    for cid, entry in v1.items():
        for s in entry["samples"]:
            if (cid, s["sample"]) in done:
                continue
            run = pipeline.run(cases[cid], s["evaluator_raw"], f"natural_improved_{VERSION}")
            runs.append({
                "case_id": cid, "sample": s["sample"],
                "v1_overall_minus_mean": s.get("overall_minus_mean"),
                "pipeline": run,
                "byte_identical_to_input": run["final_raw"] == s["evaluator_raw"],
            })
            h.dump(OUT, runs)
            print(f"[natural] {cid} s{s['sample']}: {run['status']} findings={len(run['findings'])} "
                  f"spent=${h.spent_so_far():.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
