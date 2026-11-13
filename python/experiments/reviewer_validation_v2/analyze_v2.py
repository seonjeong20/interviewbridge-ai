"""Builds the v2 comparison tables (CSV) and results/summary.json. No API calls.

The production Reviewer's numbers on the 17 original cases are read from the
v1 results (../reviewer_validation/results), not re-run.

Usage: python analyze_v2.py
"""

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

V2 = Path(__file__).resolve().parent
V1 = V2.parent / "reviewer_validation"
RES = V2 / "results"
SCORE_KEYS = ["logicalThinking", "specificity", "communication", "jobFit", "starStructure"]
DETECTABLE = ("resolve", "dedupe", "fix_overall")


def load(path):
    return json.loads(Path(path).read_text())


def write_csv(name, rows):
    with (RES / name).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def frac(n, d):
    return f"{n}/{d}"


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def gap(raw):
    ev = json.loads(raw)
    return ev["overallScore"] - sum(ev["evaluationScores"][k]["score"] for k in SCORE_KEYS) / 5


def item_scores(raw):
    ev = json.loads(raw)
    return [ev["evaluationScores"][k]["score"] for k in SCORE_KEYS]


adj = load(V2 / "ai_assisted_adjudication.json")
v1_adj = load(V1 / "manual_adjudication.json")
cases = {c["id"]: c for c in load(V1 / "test_cases.json")["cases"]}
heldout_cases = {c["id"]: c for c in load(V2 / "heldout_cases.json")["cases"]}
summary = {}

# ---------------------------------------------------------------------------
# Reviewer stage on the 17 original cases: production (v1 data) vs v2.0 vs v2.1
# ---------------------------------------------------------------------------
rows = []
for r in load(V1 / "results/exp1_reviewer_runs.json"):
    a = v1_adj["exp1"][f"{r['case_id']}#{r['rep']}"]
    rows.append({"arm": "production_reviewer", "case_id": r["case_id"], "type": r["type"],
                 "expect": r["expect"], "rep": r["rep"], "final_raw": r["reviewed_raw"],
                 "rule_verdict": r["rule"]["rule_verdict"], "adjudication": a["verdict"],
                 "adjudication_note": "", "adjudication_evidence": a["evidence"],
                 "status": "", "detected": "", "byte_identical_to_input": False,
                 "llm_calls": r["requests"], "latency_s": r["latency_s"],
                 "est_cost_usd": r["est_cost_usd"], "judge": r["judge"]})
for version, name in (("v20", "e1_main_runs.json"), ("v21", "e1_main_runs_v21.json")):
    for r in load(RES / name):
        a = adj["main"][f"{version}|{r['case_id']}#{r['rep']}"]
        rows.append({"arm": f"improved_{version}", "case_id": r["case_id"], "type": r["type"],
                     "expect": r["expect"], "rep": r["rep"], "final_raw": r["final_raw"],
                     "rule_verdict": r["rule"]["rule_verdict"], "adjudication": a["verdict"],
                     "adjudication_note": a["note"], "adjudication_evidence": a["evidence"],
                     "status": r["pipeline"]["status"], "detected": r["detected"],
                     "byte_identical_to_input": r["byte_identical_to_input"],
                     "llm_calls": r["llm_calls"], "latency_s": r["latency_s"],
                     "est_cost_usd": r["est_cost_usd"], "judge": r["judge"]})

judges = list(rows[0]["judge"].keys())
for row in rows:
    original = json.dumps(cases[row["case_id"]]["evaluator_output"], ensure_ascii=False)
    row["item_scores_changed"] = item_scores(row["final_raw"]) != item_scores(original)
    row["overall_changed"] = json.loads(row["final_raw"])["overallScore"] != cases[row["case_id"]]["evaluator_output"]["overallScore"]
    row["final_overall_minus_mean"] = round(gap(row["final_raw"]), 1)
    for j in judges:
        row[f"{j}_defect_resolved"] = row["judge"][j].get("defect_resolved")
        row[f"{j}_rationale"] = row["judge"][j].get("rationale")
write_csv("e1_reviewer_stage_by_run.csv",
          [{k: v for k, v in row.items() if k not in ("judge", "final_raw")} for row in rows])

ARMS = ["production_reviewer", "improved_v20", "improved_v21"]


def stage_stats(subset_rows, arm, case_lookup):
    rs = [r for r in subset_rows if r["arm"] == arm]
    defect = [r for r in rs if r["expect"] in DETECTABLE]
    normal = [r for r in rs if r["expect"] == "preserve"]
    out = {
        "runs": len(rs),
        "defect_runs": len(defect),
        "resolved": frac(sum(r["adjudication"] == "resolved" for r in defect), len(defect)),
        "partial": frac(sum(r["adjudication"] == "partial" for r in defect), len(defect)),
        "not_resolved": frac(sum(r["adjudication"] == "not_resolved" for r in defect), len(defect)),
        "resolved_by_case": {cid: frac(sum(r["adjudication"] == "resolved" for r in defect if r["case_id"] == cid),
                                       sum(1 for r in defect if r["case_id"] == cid))
                             for cid in sorted({r["case_id"] for r in defect})},
        "resolved_rule_check": frac(sum(r["rule_verdict"] == "resolved" for r in defect), len(defect)),
        "rule_vs_adjudication_agreement": frac(
            sum((r["rule_verdict"] == "resolved") == (r["adjudication"] == "resolved") for r in defect), len(defect)),
        "normal_runs": len(normal),
        "normal_preserved": frac(sum(r["adjudication"] == "preserved" for r in normal), len(normal)),
        "normal_byte_identical": frac(sum(bool(r["byte_identical_to_input"]) for r in normal), len(normal)),
        "runs_with_item_score_change": frac(sum(r["item_scores_changed"] for r in rs), len(rs)),
        "runs_with_overall_score_change": frac(sum(r["overall_changed"] for r in rs), len(rs)),
        "final_outputs_with_arithmetic_gap_over_1": frac(
            sum(abs(r["final_overall_minus_mean"]) > 1 for r in rs), len(rs)),
        "llm_calls_mean": mean([r["llm_calls"] for r in rs]),
        "latency_mean_s": mean([r["latency_s"] for r in rs]),
        "latency_median_s": round(statistics.median(r["latency_s"] for r in rs), 3),
        "latency_mean_normal_s": mean([r["latency_s"] for r in normal]),
        "est_cost_mean_usd": round(sum(r["est_cost_usd"] for r in rs) / len(rs), 5),
    }
    for j in judges:
        out[f"resolved_{j}"] = frac(sum(r[f"{j}_defect_resolved"] == "yes" for r in defect), len(defect))
        out[f"{j}_vs_adjudication_agreement"] = frac(
            sum((r[f"{j}_defect_resolved"] == "yes") == (r["adjudication"] == "resolved") for r in defect),
            len(defect))
    if arm != "production_reviewer":
        out["detected"] = frac(sum(r["detected"] is True for r in rs if r["detected"] != "" and r["detected"] is not None),
                               sum(1 for r in rs if r["detected"] != "" and r["detected"] is not None))
        out["detected_by_case"] = {cid: frac(sum(r["detected"] is True for r in rs if r["case_id"] == cid),
                                             sum(1 for r in rs if r["case_id"] == cid))
                                   for cid in sorted({r["case_id"] for r in rs if r["detected"] is not None and r["detected"] != ""})}
        out["status"] = dict(Counter(r["status"] for r in rs))
        out["normal_status"] = dict(Counter(r["status"] for r in normal))
        out["normal_flagged_needs_review"] = frac(sum(r["status"] == "needs_review" for r in normal), len(normal))
    return out


summary["reviewer_stage_main_17_cases"] = {arm: stage_stats(rows, arm, cases) for arm in ARMS}

# Answer-dependent case TC-13: do the facts that are not in the answer survive?
summary["tc13_unsupported_facts_remaining"] = {
    arm: frac(sum(any(k in r["final_raw"] for k in ("Kafka", "30%", "Airflow"))
                  for r in rows if r["arm"] == arm and r["case_id"] == "TC-13"), 5) for arm in ARMS}
summary["tc13_adjudication"] = {
    arm: dict(Counter(r["adjudication"] for r in rows if r["arm"] == arm and r["case_id"] == "TC-13"))
    for arm in ARMS}
summary["focus_cases"] = {
    cid: {arm: dict(Counter(r["adjudication"] for r in rows if r["arm"] == arm and r["case_id"] == cid))
          for arm in ARMS}
    for cid in ("TC-07", "TC-10", "TC-11", "TC-13", "TC-16", "TC-17")}

case_rows = []
for cid in cases:
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm and r["case_id"] == cid]
        case_rows.append({
            "case_id": cid, "type": cases[cid]["type"], "expect": cases[cid]["expect"], "arm": arm,
            "adjudication": ", ".join(f"{k}x{v}" for k, v in sorted(Counter(r["adjudication"] for r in rs).items())),
            "rule": ", ".join(f"{k}x{v}" for k, v in sorted(Counter(r["rule_verdict"] for r in rs).items())),
            "status": ", ".join(f"{k}x{v}" for k, v in sorted(Counter(r["status"] for r in rs).items())),
            "detected": frac(sum(r["detected"] is True for r in rs), len(rs)) if arm != "production_reviewer" else "",
            "byte_identical": frac(sum(bool(r["byte_identical_to_input"]) for r in rs), len(rs)),
            "item_score_changes": sum(r["item_scores_changed"] for r in rs),
            "llm_calls_mean": mean([r["llm_calls"] for r in rs]),
            "latency_mean_s": mean([r["latency_s"] for r in rs]),
        })
write_csv("e1_reviewer_stage_by_case.csv", case_rows)

# Gate outcomes of the improved pipeline
gate = {}
for version, name in (("v20", "e1_main_runs.json"), ("v21", "e1_main_runs_v21.json")):
    counter = Counter()
    for r in load(RES / name):
        p = r["pipeline"]
        findings = p["findings"] if version == "v20" else [f for ps in p["passes"] for f in ps["findings"]]
        for f in findings:
            counter["applied" if f["applied"] else f["gate_result"].split(":")[0][:60]] += 1
    gate[version] = dict(counter.most_common())
summary["gate_outcomes_main"] = gate

# ---------------------------------------------------------------------------
# Held-out cases
# ---------------------------------------------------------------------------
ho_rows = []
for name, version in (("e4_heldout_runs.json", "v20"), ("e4_heldout_runs_v21.json", "v21")):
    for r in load(RES / name):
        arm = "production_reviewer" if r["arm"] == "production_reviewer" else f"improved_{version}"
        key = ("production_reviewer" if arm == "production_reviewer" else version) + f"|{r['case_id']}#{r['rep']}"
        a = adj["heldout"][key]
        original = json.dumps(heldout_cases[r["case_id"]]["evaluator_output"], ensure_ascii=False)
        ho_rows.append({
            "arm": arm, "case_id": r["case_id"], "type": r["type"], "expect": r["expect"], "rep": r["rep"],
            "rule_verdict": r["rule"]["rule_verdict"], "adjudication": a["verdict"],
            "adjudication_note": a["note"], "adjudication_evidence": a["evidence"],
            "status": r.get("pipeline", {}).get("status", ""), "detected": r.get("detected", ""),
            "byte_identical_to_input": r["byte_identical_to_input"],
            "item_scores_changed": item_scores(r["final_raw"]) != item_scores(original),
            "overall_changed": json.loads(r["final_raw"])["overallScore"] != heldout_cases[r["case_id"]]["evaluator_output"]["overallScore"],
            "final_overall_minus_mean": round(gap(r["final_raw"]), 1),
            "llm_calls": r["llm_calls"], "latency_s": r["latency_s"], "est_cost_usd": r["est_cost_usd"],
            **{f"{j}_defect_resolved": r["judge"][j].get("defect_resolved") for j in judges},
            **{f"{j}_rationale": r["judge"][j].get("rationale") for j in judges},
        })
write_csv("e4_heldout_by_run.csv", ho_rows)
summary["reviewer_stage_heldout_8_cases"] = {arm: stage_stats(ho_rows, arm, heldout_cases) for arm in ARMS}
summary["ho05_adjudication"] = {
    arm: dict(Counter(r["adjudication"] for r in ho_rows if r["arm"] == arm and r["case_id"] == "HO-05"))
    for arm in ARMS}

# ---------------------------------------------------------------------------
# Real Evaluator outputs (51)
# ---------------------------------------------------------------------------
nat_rows, natural = [], {}
v1_nat = load(V1 / "results/exp3_self_consistency.json")
for version, name in (("v20", "e3_natural_runs.json"), ("v21", "e3_natural_runs_v21.json")):
    runs = load(RES / name)
    for r in runs:
        p = r["pipeline"]
        reviewer_edits = [c for c in p["change_log"] if c["source"] != "validator"]
        flags = (p.get("score_flags") if version == "v21"
                 else [f for f in p["findings"] if f["action"] == "flag_score"])
        nat_rows.append({
            "version": version, "case_id": r["case_id"], "sample": r["sample"], "status": p["status"],
            "byte_identical_to_input": r["byte_identical_to_input"],
            "validator_fixed_overall": any(f["check"] == "overall_score_arithmetic" for f in p["validator_report"]["fixes"]),
            "reviewer_edits": len(reviewer_edits),
            "reviewer_edit_types": "|".join(sorted({c["issue_type"] for c in reviewer_edits})),
            "removed_or_replaced": " || ".join(c["before"] for c in reviewer_edits),
            "score_flags": len(flags),
            "score_flags_code_derived": sum("S2 derived" in f.get("gate_result", "") for f in flags),
            "llm_calls": p["llm_calls"], "latency_s": p["total_latency_s"],
            "est_cost_usd": round(p["est_cost_usd"], 6),
        })
    rs = [x for x in nat_rows if x["version"] == version]
    natural[version] = {
        "runs": len(rs),
        "status": dict(Counter(x["status"] for x in rs)),
        "byte_identical": frac(sum(x["byte_identical_to_input"] for x in rs), len(rs)),
        "overall_score_fixed_by_validator": frac(sum(x["validator_fixed_overall"] for x in rs), len(rs)),
        "runs_with_reviewer_edits": frac(sum(x["reviewer_edits"] > 0 for x in rs), len(rs)),
        "reviewer_edits_total": sum(x["reviewer_edits"] for x in rs),
        "reviewer_edit_types": dict(Counter(t for x in rs for t in x["reviewer_edit_types"].split("|") if t)),
        "runs_with_score_flags": frac(sum(x["score_flags"] > 0 for x in rs), len(rs)),
        "score_flags_total": sum(x["score_flags"] for x in rs),
        "score_flags_code_derived": sum(x["score_flags_code_derived"] for x in rs),
        "llm_calls_mean": mean([x["llm_calls"] for x in rs]),
        "latency_mean_s": mean([x["latency_s"] for x in rs]),
        "latency_median_s": round(statistics.median(x["latency_s"] for x in rs), 3),
        "est_cost_mean_usd": round(sum(x["est_cost_usd"] for x in rs) / len(rs), 5),
    }
write_csv("e3_natural_by_run.csv", nat_rows)
v1_samples = [s for e in v1_nat.values() for s in e["samples"]]
natural["production_reviewer_v1_data"] = {
    "runs": len(v1_samples),
    "byte_identical": frac(sum(s["reviewer_raw"] == s["evaluator_raw"] for s in v1_samples), len(v1_samples)),
    "text_identical": frac(sum(bool(s.get("reviewer_text_identical")) for s in v1_samples), len(v1_samples)),
    "evaluator_outputs_with_gap_over_1": frac(sum(abs(s["overall_minus_mean"]) > 1 for s in v1_samples), len(v1_samples)),
    "evaluator_outputs_with_any_gap": frac(sum(abs(s["overall_minus_mean"]) >= 0.5 for s in v1_samples), len(v1_samples)),
    "reviewer_outputs_with_gap_over_1": frac(sum(abs(gap(s["reviewer_raw"])) > 1 for s in v1_samples), len(v1_samples)),
    "latency_mean_s": mean([s["reviewer_latency_s"] for s in v1_samples]),
}
summary["real_evaluator_outputs_51"] = natural

# ---------------------------------------------------------------------------
# Coach comparison
# ---------------------------------------------------------------------------
coach = load(RES / "e2_coach_runs.json")
crow = []
for r in coach:
    a = adj["coach"].get(f"{r['arm']}|{r['case_id']}#{r['rep']}")
    row = {"arm": r["arm"], "case_id": r["case_id"], "type": r["type"], "expect": r["expect"], "rep": r["rep"],
           "format_ok": r["rule"]["format_ok"],
           "carries_planted_error_adjudicated": a["carries_error"] if a else "",
           "adjudication_evidence": a["evidence"] if a else "",
           "invented_numbers_rule": "|".join(r["rule"].get("invented_numbers", [])),
           "coach_latency_s": r["coach_latency_s"],
           "post_evaluator_latency_s": r["post_evaluator_latency_s"],
           "post_evaluator_calls": r["post_evaluator_calls"]}
    for j in judges:
        v = (r["judge"] or {}).get(j, {})
        cov = v.get("weakness_coverage") or []
        row[f"{j}_contradicts"] = v.get("contradicts_evaluation")
        row[f"{j}_echoes_planted_error"] = v.get("echoes_planted_error")
        row[f"{j}_coverage"] = round(sum(bool(c.get("covered")) for c in cov) / len(cov), 2) if cov else None
        row[f"{j}_ungrounded_tips"] = v.get("ungrounded_tips")
        row[f"{j}_specificity"] = v.get("specificity")
        row[f"{j}_rationale"] = v.get("rationale")
    crow.append(row)
write_csv("e2_coach_by_run.csv", crow)

coach_summary = {}
for arm in ["A_no_reviewer", "B_production_reviewer", "C_improved", "D_improved_v21"]:
    rs = [r for r in crow if r["arm"] == arm]
    adjd = [r for r in rs if r["carries_planted_error_adjudicated"] != ""]
    stats = {
        "runs": len(rs),
        "format_ok": frac(sum(r["format_ok"] for r in rs), len(rs)),
        "carries_planted_error_adjudicated": frac(sum(r["carries_planted_error_adjudicated"] is True for r in adjd), len(adjd)),
        "carries_by_case": {cid: frac(sum(r["carries_planted_error_adjudicated"] is True for r in adjd if r["case_id"] == cid), 3)
                            for cid in sorted({r["case_id"] for r in adjd})},
        "runs_with_invented_numbers_rule": frac(sum(bool(r["invented_numbers_rule"]) for r in rs), len(rs)),
        "coach_latency_mean_s": mean([r["coach_latency_s"] for r in rs]),
        "post_evaluator_latency_mean_s": mean([r["post_evaluator_latency_s"] for r in rs]),
        "post_evaluator_calls_mean": mean([r["post_evaluator_calls"] for r in rs]),
    }
    for j in judges:
        stats[f"{j}_contradicts"] = frac(sum(r[f"{j}_contradicts"] is True for r in rs), len(rs))
        stats[f"{j}_coverage_mean"] = mean([r[f"{j}_coverage"] for r in rs])
        stats[f"{j}_ungrounded_tips_mean"] = mean([r[f"{j}_ungrounded_tips"] for r in rs])
        stats[f"{j}_specificity_mean"] = mean([r[f"{j}_specificity"] for r in rs])
        stats[f"{j}_vs_adjudication_on_planted_error"] = frac(
            sum((r[f"{j}_echoes_planted_error"] is True) == r["carries_planted_error_adjudicated"] for r in adjd), len(adjd))
    coach_summary[arm] = stats
summary["coach_comparison"] = coach_summary

# What the Coach arms were fed (run 1 of each reviewer stage) for the seven adjudicated cases
fed = {}
for cid in ("TC-07", "TC-08", "TC-09", "TC-10", "TC-11", "TC-13", "TC-16"):
    fed[cid] = {arm: next(r["adjudication"] for r in rows if r["arm"] == arm and r["case_id"] == cid and r["rep"] == 1)
                for arm in ARMS}
summary["coach_input_run1_adjudication"] = fed

# ---------------------------------------------------------------------------
# Calls, latency, cost
# ---------------------------------------------------------------------------
ledger = [json.loads(line) for line in (RES / "call_ledger.jsonl").read_text().splitlines() if line.strip()]
groups = defaultdict(list)
for e in ledger:
    groups[(e["stage"], e["model"])].append(e)
cost_rows = []
for (stage, model), es in sorted(groups.items()):
    cost_rows.append({
        "stage": stage, "model": model, "invocations": len(es),
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
    "total_est_cost_usd": round(sum(e["est_cost_usd"] for e in ledger), 4),
    "judge_est_cost_usd": round(sum(e["est_cost_usd"] for e in ledger if e["stage"] == "judge"), 4),
    "by_stage": {f"{r['stage']} ({r['model']})": r for r in cost_rows},
}

(RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=1))
