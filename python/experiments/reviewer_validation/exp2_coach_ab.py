"""Experiment 2 - Coach with and without the Reviewer.

Arm A: Evaluator output ------------------> Coach
Arm B: Evaluator output -> Reviewer output -> Coach

Controlled: same evaluator output, same question analysis, same production
Coach agent/prompt/model/temperature in both arms. The Reviewer output used
in arm B is rep 1 of experiment 1 (so exp1_reviewer.py must run first).
Each arm is run REPS times because the Coach is stochastic (temperature 0.3).

Usage: python exp2_coach_ab.py
"""

import json
import re
import sys

import harness as h

REPS = 2
OUT = "exp2_coach_runs.json"
ANALYSIS_OUT = "exp2_analyses.json"

# Consistency criteria (fixed before any coaching output was generated).
CRITERIA = {
    "C1_format": "rule: output parses with json.loads and matches schemas.CoachingResult; at most 4 tips",
    "C2_contradiction": "judge: coaching states something that contradicts the intended reading of the evaluation",
    "C3_echo": "judge + rule: coaching repeats or builds on the planted false claim",
    "C4_coverage": "judge: share of key_weaknesses addressed by at least one tip",
    "C5_ungrounded": "judge: number of tips that trace to no weakness / low-score feedback in the evaluation",
    "C6_specificity": "judge: 1-5, how specific the tips are to THIS answer",
    "C7_invented_numbers": "rule: numbers in modelAnswer.nativeLanguage that do not appear in the candidate's answer",
}

JUDGE_SYSTEM = """You audit coaching feedback produced by an AI interview-practice service.
The coach was given an evaluation of the candidate's answer and must base its advice on it.

You get: the question, the answer, the evaluation the pipeline started from, a note describing a false
claim that was deliberately planted in that evaluation (or "none"), the INTENDED reading of the
evaluation (what is actually weak), the key weaknesses, and the coaching (overall summary + tips).
You are not told how the coaching was produced. Judge only the coaching text.

Answer in JSON with exactly these keys:
- "contradicts_evaluation": true/false - does the coaching assert something that contradicts the
  intended reading (e.g. praises a dimension that is actually weak, or criticises something the answer does well)?
- "contradiction_detail": short string ("" if false)
- "echoes_planted_error": true/false/null - null when no false claim was planted; true when the
  coaching repeats, relies on, or builds advice on the planted false claim
- "echo_detail": short string
- "weakness_coverage": list of {"weakness": <string from key_weaknesses>, "covered": true/false}
- "ungrounded_tips": integer - tips that correspond to NO weakness or low-score feedback in the evaluation
- "ungrounded_detail": short string
- "specificity": integer 1-5. 5 = tips name concrete content of this answer and say exactly what to add
  or change; 3 = tips fit this type of answer but stay general; 1 = generic advice for any interview answer
- "rationale": 1-3 sentences in Korean quoting the decisive phrases."""

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def rule_checks(case, coaching_raw):
    coaching, fmt_error = h.check_coaching_format(coaching_raw)
    out = {"format_ok": fmt_error is None, "format_error": fmt_error}
    if coaching is None or fmt_error:
        return out
    text = coaching["overallSummary"] + "\n" + "\n".join(coaching["improvementTips"])
    allowed = set(NUMBER.findall(case["answer"])) | set(NUMBER.findall(case["question"]))
    invented = sorted(set(NUMBER.findall(coaching["modelAnswer"]["nativeLanguage"])) - allowed)
    out.update({
        "n_tips": len(coaching["improvementTips"]),
        "tips_within_limit": len(coaching["improvementTips"]) <= 4,
        "markers_echoed": [m for m in case["contradiction_markers"] if m in text],
        "invented_numbers": invented,
    })
    return out


def judge_run(case, coaching, tag):
    user = json.dumps({
        "question": case["question"],
        "answer": case["answer"],
        "evaluation_the_pipeline_started_from": case["evaluator_output"],
        "planted_false_claim": case["injected_error"] or "none",
        "intended_reading": case["intended_reading"],
        "key_weaknesses": case["key_weaknesses"],
        "coaching": {
            "overallSummary": coaching["overallSummary"],
            "improvementTips": coaching["improvementTips"],
        },
    }, ensure_ascii=False, indent=1)
    return h.judge(JUDGE_SYSTEM, user, case["id"], tag)


def main():
    cases = json.loads((h.EXP_DIR / "test_cases.json").read_text())["cases"]
    reviewed = {r["case_id"]: r for r in h.load("exp1_reviewer_runs.json") if r["rep"] == 1}

    apath = h.RESULTS_DIR / ANALYSIS_OUT
    analyses = json.loads(apath.read_text()) if apath.exists() else {}
    path = h.RESULTS_DIR / OUT
    runs = json.loads(path.read_text()) if path.exists() else []
    done = {(r["case_id"], r["arm"], r["rep"]) for r in runs}

    for case in cases:
        cid = case["id"]
        if cid not in analyses:
            a = h.run_analyzer(case, "exp2")
            analyses[cid] = {"raw": a["raw"], "latency_s": a["latency_s"], "requests": a["requests"]}
            h.dump(ANALYSIS_OUT, analyses)

        evaluation_raw = json.dumps(case["evaluator_output"], ensure_ascii=False, indent=2)
        arms = {"A_no_reviewer": evaluation_raw, "B_with_reviewer": reviewed[cid]["reviewed_raw"]}

        for rep in range(1, REPS + 1):
            for arm, coach_input in arms.items():
                if (cid, arm, rep) in done:
                    continue
                result = h.run_coach(case, analyses[cid]["raw"], coach_input, "exp2")
                checks = rule_checks(case, result["raw"])
                coaching, _ = h.parse_like_api(result["raw"])
                verdict = judge_run(case, coaching, "exp2_judge") if checks["format_ok"] else None
                runs.append({
                    "case_id": cid, "type": case["type"], "expect": case["expect"],
                    "arm": arm, "rep": rep,
                    "coach_raw": result["raw"],
                    "latency_s": result["latency_s"], "requests": result["requests"],
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "est_cost_usd": result["est_cost_usd"],
                    "rule": checks, "judge": verdict,
                })
                h.dump(OUT, runs)
                print(f"[exp2] {cid} {arm} rep{rep}: fmt={checks['format_ok']} "
                      f"spent=${h.spent_so_far():.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
