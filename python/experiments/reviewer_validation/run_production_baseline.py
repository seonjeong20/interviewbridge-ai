"""Run the unmodified production evaluation crew end to end.

Mirrors what python/api.py `/analyze` does, to record the real output shapes,
call counts and latency of the shipped 4-stage pipeline
(Analyzer -> Evaluator -> Reviewer -> Coach).

Usage: python run_production_baseline.py [CASE_ID ...]
"""

import json
import sys
import time

import harness as h
from src.crew import evaluation_crew

DEFAULT_CASES = ["TC-01", "TC-04"]


def main():
    wanted = sys.argv[1:] or DEFAULT_CASES
    cases = {c["id"]: c for c in json.loads((h.EXP_DIR / "test_cases.json").read_text())["cases"]}
    runs = []

    for case_id in wanted:
        case = cases[case_id]
        inputs = h.crew_inputs(case)
        # question_generation_task has not run in this process, exactly like a
        # freshly started API server that receives /analyze first.
        before = h.usage_counters()
        started = time.perf_counter()
        result = evaluation_crew.kickoff(inputs=inputs)
        latency = time.perf_counter() - started

        usage = h.usage_delta(before)
        reported = result.token_usage
        entry = {
            "tag": "production_baseline",
            "stage": "full_crew",
            "case_id": case_id,
            "model": h.SUBJECT_MODEL,
            "latency_s": round(latency, 3),
            **usage,
            "est_cost_usd": h.estimate_cost(
                h.SUBJECT_MODEL, usage["prompt_tokens"], usage["completion_tokens"],
                usage["cached_tokens"],
            ),
        }
        h._record(entry)
        runs.append({
            **entry,
            # What crewAI itself reports for this kickoff (over-counted, see harness.usage_counters).
            "crewai_reported_requests": reported.successful_requests,
            "crewai_reported_total_tokens": reported.total_tokens,
            "tasks": [{"agent": t.agent, "raw": t.raw} for t in result.tasks_output],
        })
        print(f"[baseline] {case_id}: {latency:.1f}s, {usage['requests']} requests",
              file=sys.stderr)

    h.dump("production_baseline.json", runs)


if __name__ == "__main__":
    main()
