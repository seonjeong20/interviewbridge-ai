"""Turn the raw experiment outputs into CSV tables and results/summary.json.

Makes no API calls. Usage: python analyze.py
"""

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
RESULTS = EXP_DIR / "results"
SCORE_KEYS = ["logicalThinking", "specificity", "communication", "jobFit", "starStructure"]


def load(name):
    return json.loads((RESULTS / name).read_text())


def write_csv(name, rows):
    if not rows:
        return
    with (RESULTS / name).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def frac(numerator, denominator):
    return f"{numerator}/{denominator}"


cases = {c["id"]: c for c in json.loads((EXP_DIR / "test_cases.json").read_text())["cases"]}
manual = json.loads((EXP_DIR / "manual_adjudication.json").read_text())
summary = {}

# ---------------------------------------------------------------------------
# Experiment 1
# ---------------------------------------------------------------------------
exp1 = load("exp1_reviewer_runs.json")
judges = list(exp1[0]["judge"].keys())
rows = []
for r in exp1:
    rule = r["rule"]
    adjudicated = manual["exp1"][f"{r['case_id']}#{r['rep']}"]
    row = {
        "case_id": r["case_id"], "type": r["type"], "expect": r["expect"], "rep": r["rep"],
        "format_ok": rule["format_ok"],
        "rule_verdict": rule["rule_verdict"],
        "manual_verdict": adjudicated["verdict"],
        "manual_evidence": adjudicated["evidence"],
        "score_changes": json.dumps(rule.get("score_changes", {}), ensure_ascii=False),
        "text_identical": rule.get("text_identical"),
        "text_similarity": rule.get("text_similarity"),
        "markers_remaining": "|".join(rule.get("markers_remaining", [])),
        "n_strengths_before_after": "->".join(map(str, rule.get("n_strengths", []))),
        "n_weaknesses_before_after": "->".join(map(str, rule.get("n_weaknesses", []))),
        "overall_minus_mean_before_after": "->".join(map(str, rule.get("overall_minus_mean", []))),
    }
    for j in judges:
        v = r["judge"][j]
        row[f"{j}_defect_resolved"] = v.get("defect_resolved")
        row[f"{j}_method"] = v.get("resolution_method")
        row[f"{j}_meaning_changed"] = v.get("meaning_changed")
        row[f"{j}_new_problem"] = v.get("new_problem")
        row[f"{j}_rationale"] = v.get("rationale")
    row.update({"latency_s": r["latency_s"], "requests": r["requests"],
                "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"]})
    rows.append(row)
write_csv("exp1_reviewer_by_run.csv", rows)

by_case = defaultdict(list)
for row in rows:
    by_case[row["case_id"]].append(row)
case_rows = []
for cid, rs in by_case.items():
    case_rows.append({
        "case_id": cid, "type": rs[0]["type"], "type_label": cases[cid]["type_label"],
        "expect": rs[0]["expect"], "runs": len(rs),
        "format_ok": frac(sum(r["format_ok"] for r in rs), len(rs)),
        "runs_with_score_change": frac(sum(r["score_changes"] != "{}" for r in rs), len(rs)),
        "manual_verdicts": ", ".join(f"{v}x{n}" for v, n in sorted(
            {v: [r["manual_verdict"] for r in rs].count(v) for v in {r["manual_verdict"] for r in rs}}.items())),
        "rule_verdicts": ", ".join(f"{v}x{n}" for v, n in sorted(
            {v: [r["rule_verdict"] for r in rs].count(v) for v in {r["rule_verdict"] for r in rs}}.items())),
        **{f"{j}_resolved_yes": frac(sum(r[f"{j}_defect_resolved"] == "yes" for r in rs), len(rs))
           for j in judges},
        "mean_text_similarity": mean([r["text_similarity"] for r in rs]),
    })
write_csv("exp1_reviewer_by_case.csv", case_rows)

DETECTABLE = ("resolve", "dedupe", "fix_overall")
defect_rows = [r for r in rows if r["expect"] in DETECTABLE]
normal_rows = [r for r in rows if r["expect"] == "preserve"]
blind_rows = [r for r in rows if r["expect"] == "undetectable_by_design"]


def judge_vs_manual(judge_name, subset):
    """Agreement on the binary question 'was the planted defect fully resolved?'"""
    agree = sum((r[f"{judge_name}_defect_resolved"] == "yes") == (r["manual_verdict"] == "resolved")
                for r in subset)
    return frac(agree, len(subset))


summary["exp1"] = {
    "runs": len(rows),
    "format_ok": frac(sum(r["format_ok"] for r in rows), len(rows)),
    "detectable_defect_runs": len(defect_rows),
    "resolved_manual": frac(sum(r["manual_verdict"] == "resolved" for r in defect_rows), len(defect_rows)),
    "partially_resolved_manual": frac(sum(r["manual_verdict"] == "partial" for r in defect_rows), len(defect_rows)),
    "not_resolved_manual": frac(sum(r["manual_verdict"] == "not_resolved" for r in defect_rows), len(defect_rows)),
    "resolved_rule": frac(sum(r["rule_verdict"] == "resolved" for r in defect_rows), len(defect_rows)),
    **{f"resolved_{j}": frac(sum(r[f"{j}_defect_resolved"] == "yes" for r in defect_rows), len(defect_rows))
       for j in judges},
    "rule_vs_manual_agreement": frac(
        sum((r["rule_verdict"] == "resolved") == (r["manual_verdict"] == "resolved") for r in defect_rows),
        len(defect_rows)),
    **{f"{j}_vs_manual_agreement": judge_vs_manual(j, defect_rows) for j in judges},
    "resolved_manual_by_type": {
        t: frac(sum(r["manual_verdict"] == "resolved" for r in defect_rows if r["type"] == t),
                sum(1 for r in defect_rows if r["type"] == t))
        for t in sorted({r["type"] for r in defect_rows})},
    "cases_resolved_in_every_run": sorted(
        cid for cid, rs in by_case.items()
        if rs[0]["expect"] in DETECTABLE and all(r["manual_verdict"] == "resolved" for r in rs)),
    "cases_resolved_in_no_run": sorted(
        cid for cid, rs in by_case.items()
        if rs[0]["expect"] in DETECTABLE and not any(r["manual_verdict"] == "resolved" for r in rs)),
    "normal_runs": len(normal_rows),
    "normal_scores_preserved": frac(sum(r["score_changes"] == "{}" for r in normal_rows), len(normal_rows)),
    "normal_meaning_preserved_manual": frac(
        sum(r["manual_verdict"] == "preserved" for r in normal_rows), len(normal_rows)),
    "normal_text_identical": frac(sum(bool(r["text_identical"]) for r in normal_rows), len(normal_rows)),
    "normal_mean_text_similarity": mean([r["text_similarity"] for r in normal_rows]),
    **{f"normal_meaning_changed_{j}": frac(sum(bool(r[f"{j}_meaning_changed"]) for r in normal_rows),
                                           len(normal_rows)) for j in judges},
    "all_runs_with_score_change": frac(sum(r["score_changes"] != "{}" for r in rows), len(rows)),
    "score_changes_detail": {f"{r['case_id']}#{r['rep']}": r["score_changes"]
                             for r in rows if r["score_changes"] != "{}"},
    "undetectable_by_design_runs": len(blind_rows),
    "undetectable_manual_verdicts": {f"{r['case_id']}#{r['rep']}": r["manual_verdict"] for r in blind_rows},
    "reviewer_latency_s": {"mean": mean([r["latency_s"] for r in rows]),
                           "median": round(statistics.median(r["latency_s"] for r in rows), 3),
                           "max": max(r["latency_s"] for r in rows)},
    "reviewer_requests_per_run": mean([r["requests"] for r in rows]),
}

# ---------------------------------------------------------------------------
# Experiment 2
# ---------------------------------------------------------------------------
exp2 = load("exp2_coach_runs.json")
reviewer_rep1 = {r["case_id"]: r for r in exp1 if r["rep"] == 1}
rows2 = []
for r in exp2:
    rule = r["rule"]
    key = f"{r['case_id']}|{r['arm']}|{r['rep']}"
    adjudicated = manual["exp2"].get(key)
    row = {
        "case_id": r["case_id"], "type": r["type"], "expect": r["expect"], "arm": r["arm"], "rep": r["rep"],
        "reviewer_manual_verdict_rep1": manual["exp1"][f"{r['case_id']}#1"]["verdict"],
        "format_ok": rule["format_ok"],
        "n_tips": rule.get("n_tips"),
        "markers_echoed": "|".join(rule.get("markers_echoed", [])),
        "invented_numbers": "|".join(rule.get("invented_numbers", [])),
        "manual_carries_planted_error": adjudicated["carries_error"] if adjudicated else "",
        "manual_evidence": adjudicated["evidence"] if adjudicated else "",
    }
    for j in judges:
        v = (r["judge"] or {}).get(j, {})
        coverage = v.get("weakness_coverage") or []
        row[f"{j}_contradicts"] = v.get("contradicts_evaluation")
        row[f"{j}_echoes_planted_error"] = v.get("echoes_planted_error")
        row[f"{j}_coverage"] = (round(sum(bool(c.get("covered")) for c in coverage) / len(coverage), 2)
                                if coverage else None)
        row[f"{j}_ungrounded_tips"] = v.get("ungrounded_tips")
        row[f"{j}_specificity"] = v.get("specificity")
        row[f"{j}_rationale"] = v.get("rationale")
    reviewer_latency = reviewer_rep1[r["case_id"]]["latency_s"] if r["arm"] == "B_with_reviewer" else 0.0
    row.update({
        "coach_latency_s": r["latency_s"],
        "post_evaluator_latency_s": round(r["latency_s"] + reviewer_latency, 3),
        "post_evaluator_calls": r["requests"] + (reviewer_rep1[r["case_id"]]["requests"]
                                                if r["arm"] == "B_with_reviewer" else 0),
        "coach_prompt_tokens": r["prompt_tokens"], "coach_completion_tokens": r["completion_tokens"],
    })
    rows2.append(row)
write_csv("exp2_coach_by_run.csv", rows2)

ARMS = ["A_no_reviewer", "B_with_reviewer"]


def arm_stats(subset):
    out = {}
    for arm in ARMS:
        rs = [r for r in subset if r["arm"] == arm]
        if not rs:
            continue
        stats = {
            "runs": len(rs),
            "format_ok": frac(sum(r["format_ok"] for r in rs), len(rs)),
            "runs_with_invented_numbers": frac(sum(bool(r["invented_numbers"]) for r in rs), len(rs)),
            "runs_echoing_marker_verbatim": frac(sum(bool(r["markers_echoed"]) for r in rs), len(rs)),
            "coach_latency_mean_s": mean([r["coach_latency_s"] for r in rs]),
            "post_evaluator_latency_mean_s": mean([r["post_evaluator_latency_s"] for r in rs]),
            "post_evaluator_calls_mean": mean([r["post_evaluator_calls"] for r in rs]),
        }
        adjudicated = [r for r in rs if r["manual_carries_planted_error"] != ""]
        if adjudicated:
            stats["manual_carries_planted_error"] = frac(
                sum(r["manual_carries_planted_error"] is True for r in adjudicated), len(adjudicated))
        for j in judges:
            stats[f"{j}_contradicts"] = frac(sum(r[f"{j}_contradicts"] is True for r in rs), len(rs))
            echo_rs = [r for r in rs if r[f"{j}_echoes_planted_error"] is not None]
            stats[f"{j}_echoes_planted_error"] = frac(
                sum(r[f"{j}_echoes_planted_error"] is True for r in echo_rs), len(echo_rs))
            stats[f"{j}_coverage_mean"] = mean([r[f"{j}_coverage"] for r in rs])
            stats[f"{j}_ungrounded_tips_mean"] = mean([r[f"{j}_ungrounded_tips"] for r in rs])
            stats[f"{j}_specificity_mean"] = mean([r[f"{j}_specificity"] for r in rs])
        out[arm] = stats
    return out


contradiction_cases = [cid for cid, c in cases.items() if c["expect"] == "resolve"]
fixed_cases = [cid for cid in contradiction_cases if manual["exp1"][f"{cid}#1"]["verdict"] == "resolved"]
unfixed_cases = [cid for cid in contradiction_cases if cid not in fixed_cases]

summary["exp2"] = {
    "all_cases": arm_stats(rows2),
    "normal_cases": arm_stats([r for r in rows2 if r["expect"] == "preserve"]),
    "contradiction_cases": arm_stats([r for r in rows2 if r["case_id"] in contradiction_cases]),
    "contradiction_cases_where_reviewer_fixed_it": {
        "cases": fixed_cases, **arm_stats([r for r in rows2 if r["case_id"] in fixed_cases])},
    "contradiction_cases_where_reviewer_did_not_fix_it": {
        "cases": unfixed_cases, **arm_stats([r for r in rows2 if r["case_id"] in unfixed_cases])},
}

case_rows2 = []
for cid in cases:
    for arm in ARMS:
        rs = [r for r in rows2 if r["case_id"] == cid and r["arm"] == arm]
        if not rs:
            continue
        adjudicated = [r for r in rs if r["manual_carries_planted_error"] != ""]
        case_rows2.append({
            "case_id": cid, "type": cases[cid]["type"], "expect": cases[cid]["expect"], "arm": arm,
            "reviewer_manual_verdict_rep1": rs[0]["reviewer_manual_verdict_rep1"],
            "runs": len(rs),
            "format_ok": frac(sum(r["format_ok"] for r in rs), len(rs)),
            "manual_carries_planted_error": (frac(sum(r["manual_carries_planted_error"] is True
                                                      for r in adjudicated), len(adjudicated))
                                             if adjudicated else "n/a"),
            **{f"{j}_contradicts": frac(sum(r[f"{j}_contradicts"] is True for r in rs), len(rs))
               for j in judges},
            **{f"{j}_coverage_mean": mean([r[f"{j}_coverage"] for r in rs]) for j in judges},
            **{f"{j}_ungrounded_mean": mean([r[f"{j}_ungrounded_tips"] for r in rs]) for j in judges},
            **{f"{j}_specificity_mean": mean([r[f"{j}_specificity"] for r in rs]) for j in judges},
            "runs_with_invented_numbers": frac(sum(bool(r["invented_numbers"]) for r in rs), len(rs)),
            "post_evaluator_latency_mean_s": mean([r["post_evaluator_latency_s"] for r in rs]),
        })
write_csv("exp2_coach_by_case.csv", case_rows2)

# Judge-vs-judge agreement on the two binary coaching criteria.
both = [r for r in rows2 if r["format_ok"]]
summary["exp2"]["judge_agreement"] = {
    "contradicts_evaluation": frac(
        sum(r[f"{judges[0]}_contradicts"] == r[f"{judges[1]}_contradicts"] for r in both), len(both)),
    "specificity_exact_match": frac(
        sum(r[f"{judges[0]}_specificity"] == r[f"{judges[1]}_specificity"] for r in both), len(both)),
}
adjudicated_rows = [r for r in rows2 if r["manual_carries_planted_error"] != ""]
summary["exp2"]["judge_vs_manual_on_planted_error"] = {
    j: frac(sum((r[f"{j}_echoes_planted_error"] is True) == r["manual_carries_planted_error"]
                for r in adjudicated_rows), len(adjudicated_rows))
    for j in judges}

# ---------------------------------------------------------------------------
# Experiment 3
# ---------------------------------------------------------------------------
exp3 = load("exp3_self_consistency.json")
rows3, sample_rows = [], []
for cid, e in exp3.items():
    spread = e.get("spread")
    if not spread:
        continue
    row = {"case_id": cid}
    for k in SCORE_KEYS + ["overallScore"]:
        row[f"{k}_values"] = "/".join(map(str, spread[k]["values"]))
        row[f"{k}_range"] = spread[k]["range"]
    row.update({
        "max_dimension_range": max(spread[k]["range"] for k in SCORE_KEYS),
        "pairwise_text_similarity": e["pairwise_text_similarity"],
        "aggregate_overall": e["aggregate"]["overallScore"],
        "aggregate_text_from_sample": e["aggregate_text_from_sample"],
        "aggregate_score_text_mismatch_dims": "|".join(e["aggregate_score_text_mismatch_dims"]),
        "evaluator_latency_sum_s": round(sum(s["evaluator_latency_s"] for s in e["samples"]), 2),
        "evaluator_latency_max_s": max(s["evaluator_latency_s"] for s in e["samples"]),
        "evaluator_latency_first_s": e["samples"][0]["evaluator_latency_s"],
    })
    rows3.append(row)
    for s in e["samples"]:
        j = s.get("judge", {})
        sample_rows.append({
            "case_id": cid, "sample": s["sample"],
            "evaluator_format_ok": s["evaluator_format_error"] is None,
            "overall_minus_mean": s.get("overall_minus_mean"),
            "reviewer_format_ok": s["reviewer_format_error"] is None,
            "reviewer_score_changes": json.dumps(s.get("reviewer_score_changes", {}), ensure_ascii=False),
            "reviewer_text_identical": s.get("reviewer_text_identical"),
            "reviewer_text_similarity": s.get("reviewer_text_similarity"),
            **{f"{m}_original_has_contradiction": v.get("original_has_contradiction") for m, v in j.items()},
            **{f"{m}_original_unsupported": v.get("original_unsupported_by_answer") for m, v in j.items()},
            **{f"{m}_reviewer_changed_meaning": v.get("reviewer_changed_meaning") for m, v in j.items()},
            **{f"{m}_detail": " / ".join(filter(None, [
                v.get("original_contradiction_detail"), v.get("original_unsupported_detail"),
                v.get("reviewer_change_detail")])) for m, v in j.items()},
            "evaluator_latency_s": s["evaluator_latency_s"],
            "reviewer_latency_s": s["reviewer_latency_s"],
            "evaluator_prompt_tokens": s["evaluator_prompt_tokens"],
            "evaluator_completion_tokens": s["evaluator_completion_tokens"],
        })
write_csv("exp3_self_consistency_by_case.csv", rows3)
write_csv("exp3_natural_evaluations_by_sample.csv", sample_rows)

n = len(sample_rows)
summary["exp3"] = {
    "answers": len(rows3), "samples_per_answer": 3, "natural_evaluations": n,
    "evaluator_format_ok": frac(sum(r["evaluator_format_ok"] for r in sample_rows), n),
    "overall_equals_mean_within_1": frac(
        sum(r["overall_minus_mean"] is not None and abs(r["overall_minus_mean"]) <= 1 for r in sample_rows), n),
    "answers_with_identical_overall": frac(sum(r["overallScore_range"] == 0 for r in rows3), len(rows3)),
    "overall_range_max": max(r["overallScore_range"] for r in rows3),
    "overall_range_mean": mean([r["overallScore_range"] for r in rows3]),
    "dimension_range_distribution": {
        str(v): sum(1 for r in rows3 for k in SCORE_KEYS if r[f"{k}_range"] == v)
        for v in sorted({r[f"{k}_range"] for r in rows3 for k in SCORE_KEYS})},
    "dimension_range_mean": mean([r[f"{k}_range"] for r in rows3 for k in SCORE_KEYS]),
    "pairwise_text_similarity_mean": mean([r["pairwise_text_similarity"] for r in rows3]),
    "aggregates_with_score_text_mismatch": frac(
        sum(bool(r["aggregate_score_text_mismatch_dims"]) for r in rows3), len(rows3)),
    "aggregate_overall_differs_from_first_sample": frac(
        sum(int(r["overallScore_values"].split("/")[0]) != r["aggregate_overall"] for r in rows3), len(rows3)),
    "max_abs_aggregate_minus_first_sample": max(
        abs(int(r["overallScore_values"].split("/")[0]) - r["aggregate_overall"]) for r in rows3),
    "evaluator_latency_single_mean_s": mean([r["evaluator_latency_s"] for r in sample_rows]),
    "evaluator_latency_3_sequential_mean_s": mean([r["evaluator_latency_sum_s"] for r in rows3]),
    "evaluator_latency_3_parallel_estimate_mean_s": mean([r["evaluator_latency_max_s"] for r in rows3]),
    "evaluator_tokens_mean": {"prompt": mean([r["evaluator_prompt_tokens"] for r in sample_rows]),
                              "completion": mean([r["evaluator_completion_tokens"] for r in sample_rows])},
    "reviewer_on_natural": {
        "format_ok": frac(sum(r["reviewer_format_ok"] for r in sample_rows), n),
        "runs_with_score_change": frac(sum(r["reviewer_score_changes"] != "{}" for r in sample_rows), n),
        "text_identical": frac(sum(bool(r["reviewer_text_identical"]) for r in sample_rows), n),
        "text_similarity_mean": mean([r["reviewer_text_similarity"] for r in sample_rows]),
        "text_similarity_min": min(r["reviewer_text_similarity"] for r in sample_rows
                                   if r["reviewer_text_similarity"] is not None),
        **{f"{j}_original_has_contradiction": frac(
            sum(r.get(f"{j}_original_has_contradiction") is True for r in sample_rows), n) for j in judges},
        **{f"{j}_original_unsupported": frac(
            sum(r.get(f"{j}_original_unsupported") is True for r in sample_rows), n) for j in judges},
        **{f"{j}_reviewer_changed_meaning": frac(
            sum(r.get(f"{j}_reviewer_changed_meaning") is True for r in sample_rows), n) for j in judges},
        "reviewer_latency_mean_s": mean([r["reviewer_latency_s"] for r in sample_rows]),
    },
}

# ---------------------------------------------------------------------------
# Calls, latency, cost (from the ledger written at call time)
# ---------------------------------------------------------------------------
ledger = [json.loads(line) for line in (RESULTS / "call_ledger.jsonl").read_text().splitlines() if line.strip()]
groups = defaultdict(list)
for e in ledger:
    groups[(e["stage"], e["model"])].append(e)
cost_rows = []
for (stage, model), es in sorted(groups.items()):
    cost_rows.append({
        "stage": stage, "model": model, "invocations": len(es),
        "api_requests": sum(e["requests"] for e in es),
        "prompt_tokens": sum(e["prompt_tokens"] for e in es),
        "completion_tokens": sum(e["completion_tokens"] for e in es),
        "prompt_tokens_mean": round(sum(e["prompt_tokens"] for e in es) / len(es)),
        "completion_tokens_mean": round(sum(e["completion_tokens"] for e in es) / len(es)),
        "latency_mean_s": mean([e["latency_s"] for e in es]),
        "latency_median_s": round(statistics.median(e["latency_s"] for e in es), 3),
        "est_cost_usd_total": round(sum(e["est_cost_usd"] for e in es), 4),
        "est_cost_usd_per_invocation": round(sum(e["est_cost_usd"] for e in es) / len(es), 5),
    })
write_csv("calls_latency_cost_by_stage.csv", cost_rows)
summary["cost"] = {
    "total_invocations": len(ledger),
    "total_api_requests": sum(e["requests"] for e in ledger),
    "total_est_cost_usd": round(sum(e["est_cost_usd"] for e in ledger), 4),
    "subject_model_est_cost_usd": round(sum(e["est_cost_usd"] for e in ledger if e["stage"] != "judge"), 4),
    "judge_est_cost_usd": round(sum(e["est_cost_usd"] for e in ledger if e["stage"] == "judge"), 4),
    "by_stage": {f"{r['stage']} ({r['model']})": r for r in cost_rows},
}

(RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
