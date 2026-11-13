"""Experiment 1 - Reviewer in isolation.

Feeds each hand-written evaluator output to the production Reviewer
(reflection_agent + reflection_task prompt) REPS times and records what it
changed. Rule-based checks are computed here; an LLM judge adds a second,
fallible opinion whose rationale is stored next to the verdict.

Usage: python exp1_reviewer.py
"""

import json
import os
import sys
from difflib import SequenceMatcher

import harness as h

REPS = int(os.getenv("EXP1_REPS", "5"))
OUT = "exp1_reviewer_runs.json"

JUDGE_SYSTEM = """You audit the output of an "evaluation reviewer" in an AI interview-practice service.
The reviewer receives an interview evaluation (JSON, scores 0-100) and returns a revised evaluation.
It never sees the interview question or the candidate's answer.

You are given the question, the answer, the ORIGINAL evaluation, the REVIEWED evaluation,
and a note saying which defect (if any) was deliberately planted in the original.

Answer in JSON with exactly these keys:
- "defect_resolved": "yes" | "partial" | "no" | "n/a"   ("n/a" only when no defect was planted)
- "resolution_method": "text_edit" | "score_change" | "both" | "none"
- "meaning_changed": true/false - did the reviewer change the MEANING of any part that was not defective?
  Rephrasing, shortening or merging that keeps the meaning is NOT a meaning change.
- "meaning_change_detail": short string ("" if false)
- "new_problem": true/false - did the reviewer introduce a new contradiction, or add claims about the
  answer that were not in the original evaluation?
- "new_problem_detail": short string ("" if false)
- "rationale": 1-3 sentences, in Korean, quoting the decisive phrases."""


def near_duplicate_pairs(items, threshold=0.6):
    pairs = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if SequenceMatcher(None, items[i], items[j]).ratio() >= threshold:
                pairs += 1
    return pairs


def overall_gap(evaluation):
    scores = h.scores_of(evaluation)
    mean = sum(scores[k] for k in h.SCORE_KEYS) / len(h.SCORE_KEYS)
    return round(scores["overallScore"] - mean, 1)


def rule_checks(case, reviewed_raw):
    original = case["evaluator_output"]
    reviewed, fmt_error = h.check_evaluation_format(reviewed_raw)
    out = {"format_ok": fmt_error is None, "format_error": fmt_error}
    if reviewed is None or fmt_error:
        out["rule_verdict"] = "format_broken"
        return out

    before, after = h.scores_of(original), h.scores_of(reviewed)
    changed = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
    text = h.evaluation_text(reviewed)
    remaining = [m for m in case["contradiction_markers"] if m in text]

    out.update({
        "score_changes": changed,
        "text_similarity": round(SequenceMatcher(None, h.evaluation_text(original), text).ratio(), 3),
        "text_identical": h.evaluation_text(original) == text,
        "markers_remaining": remaining,
        "n_strengths": [len(original["strengths"]), len(reviewed["strengths"])],
        "n_weaknesses": [len(original["weaknesses"]), len(reviewed["weaknesses"])],
        "overall_minus_mean": [overall_gap(original), overall_gap(reviewed)],
    })

    expect = case["expect"]
    if expect == "preserve":
        verdict = "preserved" if not changed else "score_changed"
    elif expect == "resolve":
        rule = case["resolve_rule"]
        if "markers_absent" in rule:
            verdict = "resolved" if not remaining else "not_resolved"
        else:
            (dim, limit), = rule["score_at_most"].items()
            verdict = "resolved" if after[dim] <= limit else "not_resolved"
    elif expect == "dedupe":
        rule = case["dedupe_rule"]
        ok = all(len(reviewed[key.replace("_max", "")]) <= limit for key, limit in rule.items())
        verdict = "resolved" if ok else "not_resolved"
    elif expect == "fix_overall":
        verdict = "resolved" if abs(overall_gap(reviewed)) <= 1 else "not_resolved"
    else:  # undetectable_by_design
        verdict = "not_detected" if remaining or not case["contradiction_markers"] else "changed"
    out["rule_verdict"] = verdict
    return out


def judge_run(case, reviewed_raw, tag):
    user = json.dumps({
        "question": case["question"],
        "answer": case["answer"],
        "planted_defect": case["injected_error"] or "none (the original evaluation is defect-free)",
        "original_evaluation": case["evaluator_output"],
        "reviewed_evaluation_raw": reviewed_raw,
    }, ensure_ascii=False, indent=1)
    return h.judge(JUDGE_SYSTEM, user, case["id"], tag)


def main():
    cases = json.loads((h.EXP_DIR / "test_cases.json").read_text())["cases"]
    path = h.RESULTS_DIR / OUT
    runs = json.loads(path.read_text()) if path.exists() else []
    done = {(r["case_id"], r["rep"]) for r in runs}

    for case in cases:
        evaluation_raw = json.dumps(case["evaluator_output"], ensure_ascii=False, indent=2)
        for rep in range(1, REPS + 1):
            if (case["id"], rep) in done:
                continue
            result = h.run_reviewer(case, evaluation_raw, "exp1")
            checks = rule_checks(case, result["raw"])
            verdict = judge_run(case, result["raw"], "exp1_judge")
            runs.append({
                "case_id": case["id"], "type": case["type"], "expect": case["expect"], "rep": rep,
                "reviewed_raw": result["raw"],
                "latency_s": result["latency_s"], "requests": result["requests"],
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "est_cost_usd": result["est_cost_usd"],
                "rule": checks, "judge": verdict,
            })
            h.dump(OUT, runs)
            print(f"[exp1] {case['id']} rep{rep}: rule={checks['rule_verdict']} "
                  f"judge={[v.get('defect_resolved') for v in verdict.values()]} spent=${h.spent_so_far():.3f}",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
