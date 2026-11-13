"""Reviewer-stage comparison on fixed evaluator outputs.

  python run_reviewer_comparison.py main      # 17 original cases, improved pipeline, 5 runs each
                                              # (the production Reviewer's 85 runs are the v1 results)
  python run_reviewer_comparison.py heldout   # 8 held-out cases, production Reviewer AND improved
                                              # pipeline, 3 runs each

Scoring reuses v1 unchanged: exp1_reviewer.rule_checks and the v1 judge prompt.
"""

import json
import sys

import importlib
import os

import v2harness
import harness as h
import exp1_reviewer as v1
import prereg

# PIPELINE_VERSION=v21 runs revision 2.1 and writes to *_v21.json, leaving the
# v2.0 results in place. The production Reviewer arm is not repeated for v21.
VERSION = os.getenv("PIPELINE_VERSION", "v20")
pipeline = importlib.import_module("pipeline_v21" if VERSION == "v21" else "pipeline")

SETS = {
    "main": {"reps": 5, "arms": ["improved"], "out": "e1_main_runs.json"},
    "heldout": {"reps": 3, "arms": ["production_reviewer", "improved"], "out": "e4_heldout_runs.json"},
}


def main(name):
    cfg = dict(SETS[name])
    if VERSION == "v21":
        cfg["arms"] = ["improved"]
        cfg["out"] = cfg["out"].replace(".json", "_v21.json")
    cases = (v2harness.load_cases() if name == "main"
             else json.loads((v2harness.V2_DIR / "heldout_cases.json").read_text())["cases"])
    path = h.RESULTS_DIR / cfg["out"]
    runs = json.loads(path.read_text()) if path.exists() else []
    done = {(r["case_id"], r["arm"], r["rep"]) for r in runs}

    for case in cases:
        raw = v2harness.evaluator_raw(case)
        for rep in range(1, cfg["reps"] + 1):
            for arm in cfg["arms"]:
                if (case["id"], arm, rep) in done:
                    continue
                record = {"case_id": case["id"], "type": case["type"], "expect": case["expect"],
                          "arm": arm, "rep": rep}
                if arm == "improved":
                    run = pipeline.run(case, raw, f"{name}_improved_{VERSION}")
                    final_raw = run["final_raw"]
                    record.update({"pipeline": run, "detected": prereg.detected(case["id"], run),
                                   "latency_s": run["total_latency_s"], "llm_calls": run["llm_calls"],
                                   "est_cost_usd": run["est_cost_usd"]})
                else:
                    result = h.run_reviewer(case, raw, f"{name}_production_reviewer")
                    final_raw = result["raw"]
                    record.update({"latency_s": result["latency_s"], "llm_calls": result["requests"],
                                   "est_cost_usd": result["est_cost_usd"]})
                record["final_raw"] = final_raw
                record["byte_identical_to_input"] = final_raw == raw
                record["rule"] = v1.rule_checks(case, final_raw)
                record["judge"] = v1.judge_run(case, final_raw, f"{name}_judge_{VERSION}")
                runs.append(record)
                h.dump(cfg["out"], runs)
                print(f"[{name}] {case['id']} {arm} rep{rep}: rule={record['rule']['rule_verdict']} "
                      f"status={record.get('pipeline', {}).get('status')} spent=${h.spent_so_far():.3f}",
                      file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
