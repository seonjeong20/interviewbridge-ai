"""Improved verification pipeline (path C).

Evaluator output
  -> Deterministic Validator      (code)   schema, range, arithmetic, exact duplicates
  -> Context-Aware Reviewer       (1 LLM call) findings with quotes, no rewriting
  -> Controlled Correction        (code)   applies only verified, high-confidence edits
  -> post-check                   (code + 1 LLM call, ONLY if an edit was applied)
  -> evaluation for the Coach, in the unchanged production schema

If nothing has to change, the Evaluator's original string is passed on byte
for byte.
"""

import json
import time

import context_reviewer
import correction
import validator


def run(case, evaluation_raw, tag):
    """case needs: id, question, answer. Returns a dict describing the run."""
    out = {"llm_calls": 0, "llm_latency_s": 0.0, "est_cost_usd": 0.0,
           "prompt_tokens": 0, "completion_tokens": 0}
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
                    "change_log": [], "needs_review": True, "changed": False,
                    "post_check": {"ran": False, "residual_findings": []},
                    "total_latency_s": round(time.perf_counter() - started, 3)})
        return out

    def call_reviewer(current, current_report, stage):
        findings, entry = context_reviewer.review(
            case["question"], case["answer"], current, current_report, case["id"], tag, stage)
        out["llm_calls"] += 1
        out["llm_latency_s"] = round(out["llm_latency_s"] + entry["latency_s"], 3)
        out["est_cost_usd"] += entry["est_cost_usd"]
        out["prompt_tokens"] += entry["prompt_tokens"]
        out["completion_tokens"] += entry["completion_tokens"]
        return findings

    findings = call_reviewer(evaluation, report, "context_reviewer")

    t0 = time.perf_counter()
    corrected, dispositions, reviewer_changes = correction.apply_findings(
        evaluation, findings, case["question"], case["answer"])
    out["correction_ms"] = round((time.perf_counter() - t0) * 1000, 3)
    change_log += reviewer_changes
    out["findings"] = [{**f, **d} for f, d in zip(findings, dispositions)]

    post_check = {"ran": False, "residual_findings": [], "validator_report": None}
    if reviewer_changes:
        # Did the edits create anything new? Re-run the code checks and ask the
        # reviewer once more. Residual findings are recorded, never applied.
        _, recheck = validator.validate(json.dumps(corrected, ensure_ascii=False))
        post_check = {"ran": True, "validator_report": recheck,
                      "residual_findings": call_reviewer(corrected, recheck, "post_check")}
    out["post_check"] = post_check

    held = [f for f in out["findings"] if not f["applied"]]
    out["changed"] = bool(change_log)
    out["needs_review"] = bool(held or post_check["residual_findings"])
    out["status"] = ("needs_review" if out["needs_review"]
                     else "corrected" if out["changed"] else "clean")
    out["change_log"] = change_log
    out["final_raw"] = (json.dumps(corrected, ensure_ascii=False, indent=2)
                        if out["changed"] else evaluation_raw)
    out["total_latency_s"] = round(time.perf_counter() - started, 3)
    return out
