"""Experiment 3 - Self-Consistency on the Evaluator.

Runs the production Evaluator N_SAMPLES times on the same answer, measures the
spread, aggregates the samples, and then passes every natural (non-synthetic)
evaluator output through the production Reviewer to see what the Reviewer
does to real evaluations.

Aggregation rule (fixed before running):
  score per dimension = median of the samples
  overallScore        = round(mean of the five aggregated scores)
  text fields         = taken from the "medoid" sample, i.e. the sample whose
                        five scores are closest (L1) to the medians

Usage: python exp3_self_consistency.py
"""

import json
import statistics
import sys
from difflib import SequenceMatcher
from itertools import combinations

import harness as h

N_SAMPLES = 3
# First pass used six answers; it was then extended to every answer in the
# dataset (only the question/answer of a case is used here, never its
# hand-written evaluator output).
FIRST_PASS = ["TC-01", "TC-02", "TC-03", "TC-04", "TC-09", "TC-10"]
OUT = "exp3_self_consistency.json"

JUDGE_SYSTEM = """You audit an interview evaluation produced by an AI evaluator (JSON, scores 0-100) and the
version returned by a reviewer that is supposed to fix internal inconsistencies.

You get the question, the answer, the ORIGINAL evaluation and the REVIEWED evaluation.

Answer in JSON with exactly these keys:
- "original_has_contradiction": true/false - does the ORIGINAL contain an internal contradiction
  (score vs its feedback, summary vs feedback, strengths vs weaknesses, or two items stating opposite facts)?
  A low score with critical feedback, or mixed strengths and weaknesses, is NOT a contradiction.
- "original_contradiction_detail": short string ("" if false)
- "original_unsupported_by_answer": true/false - does the ORIGINAL cite facts that are not in the answer?
- "original_unsupported_detail": short string
- "reviewer_changed_meaning": true/false - meaning change beyond rephrasing/merging
- "reviewer_change_detail": short string
- "reviewer_introduced_problem": true/false
- "rationale": 1-3 sentences in Korean."""


def aggregate(samples):
    medians = {k: statistics.median(s["evaluationScores"][k]["score"] for s in samples)
               for k in h.SCORE_KEYS}
    medians = {k: int(round(v)) for k, v in medians.items()}

    def distance(sample):
        return sum(abs(sample["evaluationScores"][k]["score"] - medians[k]) for k in h.SCORE_KEYS)

    medoid_index = min(range(len(samples)), key=lambda i: distance(samples[i]))
    medoid = samples[medoid_index]
    merged = json.loads(json.dumps(medoid))
    for k in h.SCORE_KEYS:
        merged["evaluationScores"][k]["score"] = medians[k]
    merged["overallScore"] = int(round(sum(medians.values()) / len(medians)))
    # Dimensions where the aggregated score no longer equals the score that the
    # borrowed feedback text was written for.
    mismatched = [k for k in h.SCORE_KEYS if medoid["evaluationScores"][k]["score"] != medians[k]]
    return merged, medoid_index, mismatched


def spread(samples):
    out = {}
    for k in h.SCORE_KEYS + ["overallScore"]:
        values = [h.scores_of(s)[k] for s in samples]
        out[k] = {"values": values, "range": max(values) - min(values),
                  "sd": round(statistics.stdev(values), 2)}
    return out


def pairwise_text_similarity(samples):
    ratios = [SequenceMatcher(None, h.evaluation_text(a), h.evaluation_text(b)).ratio()
              for a, b in combinations(samples, 2)]
    return round(sum(ratios) / len(ratios), 3)


def main():
    cases = {c["id"]: c for c in json.loads((h.EXP_DIR / "test_cases.json").read_text())["cases"]}
    path = h.RESULTS_DIR / OUT
    results = json.loads(path.read_text()) if path.exists() else {}

    for cid in FIRST_PASS + [c for c in cases if c not in FIRST_PASS]:
        if cid in results:
            continue
        case = cases[cid]
        analysis = h.run_analyzer(case, "exp3")
        samples = []
        for i in range(1, N_SAMPLES + 1):
            ev = h.run_evaluator(case, analysis["raw"], "exp3")
            obj, fmt_error = h.check_evaluation_format(ev["raw"])
            rv = h.run_reviewer(case, ev["raw"], "exp3_reviewer")
            rv_obj, rv_fmt_error = h.check_evaluation_format(rv["raw"])
            sample = {
                "sample": i,
                "evaluator_raw": ev["raw"], "evaluator_format_error": fmt_error,
                "evaluator_latency_s": ev["latency_s"], "evaluator_requests": ev["requests"],
                "evaluator_prompt_tokens": ev["prompt_tokens"],
                "evaluator_completion_tokens": ev["completion_tokens"],
                "evaluator_est_cost_usd": ev["est_cost_usd"],
                "reviewer_raw": rv["raw"], "reviewer_format_error": rv_fmt_error,
                "reviewer_latency_s": rv["latency_s"],
            }
            if obj and not fmt_error:
                mean = sum(h.scores_of(obj)[k] for k in h.SCORE_KEYS) / 5
                sample["overall_minus_mean"] = round(obj["overallScore"] - mean, 1)
            if obj and rv_obj and not fmt_error and not rv_fmt_error:
                before, after = h.scores_of(obj), h.scores_of(rv_obj)
                sample["reviewer_score_changes"] = {
                    k: [before[k], after[k]] for k in before if before[k] != after[k]}
                sample["reviewer_text_identical"] = h.evaluation_text(obj) == h.evaluation_text(rv_obj)
                sample["reviewer_text_similarity"] = round(SequenceMatcher(
                    None, h.evaluation_text(obj), h.evaluation_text(rv_obj)).ratio(), 3)
                sample["judge"] = h.judge(JUDGE_SYSTEM, json.dumps({
                    "question": case["question"], "answer": case["answer"],
                    "original_evaluation": obj, "reviewed_evaluation": rv_obj,
                }, ensure_ascii=False, indent=1), cid, "exp3_judge")
            samples.append(sample)

        parsed = [json.loads(s["evaluator_raw"]) for s in samples if not s["evaluator_format_error"]]
        entry = {"case_id": cid, "analysis_raw": analysis["raw"], "samples": samples}
        if len(parsed) == N_SAMPLES:
            merged, medoid_index, mismatched = aggregate(parsed)
            entry.update({
                "spread": spread(parsed),
                "pairwise_text_similarity": pairwise_text_similarity(parsed),
                "aggregate": merged,
                "aggregate_text_from_sample": medoid_index + 1,
                "aggregate_score_text_mismatch_dims": mismatched,
            })
        results[cid] = entry
        h.dump(OUT, results)
        print(f"[exp3] {cid}: overall={entry.get('spread', {}).get('overallScore')} "
              f"spent=${h.spent_so_far():.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
