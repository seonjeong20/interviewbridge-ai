"""Improved verification pipeline, revision 2.1.

Evaluator output
  -> Deterministic Validator   (code)
  -> Context-Aware Reviewer    (LLM call 1: claim check, findings by ID, duplicate groups)
  -> Controlled Correction     (code, gated)
  -> second pass               (LLM call 2 + gated correction, ONLY if pass 1 edited something)
  -> evaluation for the Coach, production schema unchanged

At most two LLM calls. If nothing changes, the Evaluator's string is passed on
byte for byte.
"""

import json
import time

import context_reviewer_v21 as reviewer
import correction_v21 as correction
import validator

VERSION = "2.1"


def run(case, evaluation_raw, tag):
    out = {"version": VERSION, "llm_calls": 0, "llm_latency_s": 0.0, "est_cost_usd": 0.0,
           "prompt_tokens": 0, "completion_tokens": 0, "passes": []}
    started = time.perf_counter()

    t0 = time.perf_counter()
    evaluation, report = validator.validate(evaluation_raw)
    out["validator_ms"] = round((time.perf_counter() - t0) * 1000, 3)
    out["validator_report"] = report
    change_log = [{"source": "validator", "field": f["field"], "issue_type": f["check"],
                   "before": f["before"], "after": f["after"], "reason": f["reason"]}
                  for f in report["fixes"]]

    if not report["valid"]:
        out.update({"status": "invalid", "final_raw": evaluation_raw, "findings": [],
                    "change_log": [], "needs_review": True, "changed": False, "score_flags": [],
                    "total_latency_s": round(time.perf_counter() - started, 3)})
        return out

    current, current_report, code_ms = evaluation, report, 0.0
    for stage in ("context_reviewer", "second_pass"):
        review, ids, entry = reviewer.review(
            case["question"], case["answer"], current, current_report, case["id"], tag, stage)
        out["llm_calls"] += 1
        out["llm_latency_s"] = round(out["llm_latency_s"] + entry["latency_s"], 3)
        out["est_cost_usd"] += entry["est_cost_usd"]
        out["prompt_tokens"] += entry["prompt_tokens"]
        out["completion_tokens"] += entry["completion_tokens"]

        t0 = time.perf_counter()
        current, findings, groups, changes = correction.apply_review(
            current, review, ids, case["question"], case["answer"])
        code_ms += (time.perf_counter() - t0) * 1000
        change_log += changes
        out["passes"].append({"stage": stage, "claim_check": review["claim_check"],
                              "findings": findings, "duplicate_groups": groups,
                              "edits_applied": len(changes)})
        if not changes:
            break
        _, current_report = validator.validate(json.dumps(current, ensure_ascii=False))

    out["correction_ms"] = round(code_ms, 3)
    last = out["passes"][-1]
    # Flat view of pass 1 for the detection metric; the last pass decides what is still open.
    out["findings"] = out["passes"][0]["findings"]
    out["duplicate_groups"] = out["passes"][0]["duplicate_groups"]
    open_findings = [f for f in last["findings"]
                     if not f["applied"] and not f["gate_result"].startswith("S1 dismissed")]
    out["score_flags"] = [f for f in open_findings if f["defective_side"] == "score"]
    out["open_findings"] = open_findings
    # Edits made in the second pass were not re-checked by a third call.
    out["unverified_second_pass_edits"] = last["edits_applied"] if len(out["passes"]) == 2 else 0
    out["changed"] = bool(change_log)
    out["needs_review"] = bool(open_findings or out["unverified_second_pass_edits"])
    out["status"] = ("needs_review" if out["needs_review"]
                     else "corrected" if out["changed"] else "clean")
    out["change_log"] = change_log
    out["final_raw"] = (json.dumps(current, ensure_ascii=False, indent=2)
                        if out["changed"] else evaluation_raw)
    out["total_latency_s"] = round(time.perf_counter() - started, 3)
    return out
