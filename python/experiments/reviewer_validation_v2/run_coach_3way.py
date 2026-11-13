"""Three-way Coach comparison on identical Evaluator outputs.

  A  Evaluator output -----------------------------------------------> Coach
  B  Evaluator output -> production Reviewer ------------------------> Coach
  C  Evaluator output -> Validator -> Context Reviewer -> Correction -> Coach

Controlled: the Evaluator output (hand-written, from test_cases.json), the
question analysis (the one generated in v1, exp2_analyses.json), and the
production Coach agent, prompt, model and temperature are identical across
arms. Arm B uses the production Reviewer output from v1 (exp1, run 1), arm C
the improved pipeline output from e1_main_runs.json (run 1). All three arms
are run fresh here, interleaved, REPS times each.

Scoring reuses v1 unchanged: exp2_coach_ab.rule_checks and its judge prompt.

Usage: python run_coach_3way.py   (after run_reviewer_comparison.py main)
"""

import json
import os
import sys

import v2harness
import harness as h
import exp2_coach_ab as v1

REPS = 3
OUT = "e2_coach_runs.json"


def main():
    cases = v2harness.load_cases()
    analyses = v2harness.load_v1("exp2_analyses.json")
    old = {r["case_id"]: r for r in v2harness.load_v1("exp1_reviewer_runs.json") if r["rep"] == 1}
    new = {r["case_id"]: r for r in h.load("e1_main_runs.json") if r["rep"] == 1}

    # COACH_ARM_D=1 adds revision 2.1 as a fourth arm (run after arms A-C).
    new21 = None
    if os.getenv("COACH_ARM_D"):
        new21 = {r["case_id"]: r for r in h.load("e1_main_runs_v21.json") if r["rep"] == 1}

    path = h.RESULTS_DIR / OUT
    runs = json.loads(path.read_text()) if path.exists() else []
    done = {(r["case_id"], r["arm"], r["rep"]) for r in runs}

    for case in cases:
        cid = case["id"]
        arms = {
            "A_no_reviewer": (v2harness.evaluator_raw(case), 0.0, 0),
            "B_production_reviewer": (old[cid]["reviewed_raw"], old[cid]["latency_s"], old[cid]["requests"]),
            "C_improved": (new[cid]["final_raw"], new[cid]["latency_s"], new[cid]["llm_calls"]),
        }
        if new21 is not None:
            arms = {"D_improved_v21": (new21[cid]["final_raw"], new21[cid]["latency_s"],
                                       new21[cid]["llm_calls"])}
        for rep in range(1, REPS + 1):
            for arm, (coach_input, upstream_latency, upstream_calls) in arms.items():
                if (cid, arm, rep) in done:
                    continue
                result = h.run_coach(case, analyses[cid]["raw"], coach_input, "coach_3way")
                checks = v1.rule_checks(case, result["raw"])
                coaching, _ = h.parse_like_api(result["raw"])
                verdict = v1.judge_run(case, coaching, "coach_3way_judge") if checks["format_ok"] else None
                runs.append({
                    "case_id": cid, "type": case["type"], "expect": case["expect"], "arm": arm, "rep": rep,
                    "coach_raw": result["raw"], "coach_latency_s": result["latency_s"],
                    "coach_requests": result["requests"],
                    "post_evaluator_latency_s": round(result["latency_s"] + upstream_latency, 3),
                    "post_evaluator_calls": result["requests"] + upstream_calls,
                    "coach_est_cost_usd": result["est_cost_usd"],
                    "rule": checks, "judge": verdict,
                })
                h.dump(OUT, runs)
                print(f"[coach] {cid} {arm} rep{rep} spent=${h.spent_so_far():.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
