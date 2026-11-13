"""Shared helpers for the Reviewer / Self-Consistency validation experiments.

Nothing here modifies the service code. The production agents and the
production task prompts (description / expected_output) are imported and
reused as-is; only the *wiring* is rebuilt so that a fixed upstream output
can be injected as task context.
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

EXP_DIR = Path(__file__).resolve().parent
PYTHON_DIR = EXP_DIR.parents[1]
RESULTS_DIR = EXP_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)
LEDGER = RESULTS_DIR / "call_ledger.jsonl"

sys.path.insert(0, str(PYTHON_DIR))

from crewai import Crew, Process, Task  # noqa: E402
from crewai.tasks.task_output import TaskOutput  # noqa: E402

from schemas import CoachingResult, EvaluationResult  # noqa: E402
from src import agents as prod_agents  # noqa: E402
from src import tasks as prod_tasks  # noqa: E402
from src.config import COUNTRY_PROFILE, OPENAI_API_KEY, llm  # noqa: E402

SUBJECT_MODEL = llm.model
# The project key can only reach gpt-4.1-mini and gpt-4o-mini (gpt-4.1, gpt-4o,
# gpt-5* return 403), so a larger judge model is not available. Two judges are
# used instead: the model under test with a different, ground-truth-informed
# prompt, and a model from another family. Their agreement is reported.
JUDGE_MODELS = os.getenv("JUDGE_MODELS", "gpt-4.1-mini,gpt-4o-mini").split(",")

# USD per 1M tokens (input, cached input, output). OpenAI list prices as known
# to the author of this script; cost figures derived from them are ESTIMATES.
PRICES = {
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-4o-mini": (0.15, 0.075, 0.60),
}
BUDGET_USD = float(os.getenv("EXPERIMENT_BUDGET_USD", "2.0"))
BUDGET_STOP_USD = BUDGET_USD * 0.9

SCORE_KEYS = ["logicalThinking", "specificity", "communication", "jobFit", "starStructure"]


class BudgetExceeded(RuntimeError):
    pass


# ----------------------------------------------------------------------------
# Cost ledger (shared across processes through an append-only JSONL file)
# ----------------------------------------------------------------------------

def estimate_cost(model, prompt_tokens, completion_tokens, cached_tokens=0):
    p_in, p_cached, p_out = PRICES[model]
    fresh = max(prompt_tokens - cached_tokens, 0)
    return (fresh * p_in + cached_tokens * p_cached + completion_tokens * p_out) / 1_000_000


def spent_so_far():
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        if line.strip():
            total += json.loads(line)["est_cost_usd"]
    return total


def _check_budget():
    spent = spent_so_far()
    if spent >= BUDGET_STOP_USD:
        raise BudgetExceeded(
            f"estimated spend ${spent:.3f} reached the stop line ${BUDGET_STOP_USD:.2f}"
        )


def _record(entry):
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------
# Running one production stage with injected context
# ----------------------------------------------------------------------------

def crew_inputs(case):
    profile = COUNTRY_PROFILE[case["country"]]
    return {
        "job": case["job"],
        "country": case["country"],
        "native_language": case["native_language"],
        "target_language": profile["language"],
        "culture": profile["culture"],
        "style": profile["style"],
        "question": case["question"],
        "answer": case["answer"],
    }


def _fixed_output_task(agent, raw):
    """A never-executed task whose output is preset, used only as context."""
    task = Task(description="(fixed upstream output)", expected_output="(fixed)", agent=agent)
    task.output = TaskOutput(description="(fixed upstream output)", raw=raw, agent=agent.role)
    return task


def usage_counters():
    """Lifetime counters of the single LLM instance shared by every agent.

    crew.kickoff().token_usage is NOT per call: crewAI sums the lifetime
    counters of each agent's llm, and all production agents share one llm
    object, so the 4-agent production crew reports 4x the real usage. Per-call
    usage is therefore taken as a before/after difference of these counters.
    """
    u = llm.get_token_usage_summary()
    return {
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "cached_tokens": u.cached_prompt_tokens,
        "requests": u.successful_requests,
    }


def usage_delta(before):
    after = usage_counters()
    return {k: after[k] - before[k] for k in after}


def run_stage(stage, prod_task, case, context, tag):
    """Run a single production task (same agent, same prompt) once.

    context: list of (agent, raw_text) pairs that play the role of the
    upstream task outputs the production crew would have passed.
    """
    _check_budget()
    task = Task(
        description=prod_task.description,
        expected_output=prod_task.expected_output,
        agent=prod_task.agent,
        context=[_fixed_output_task(a, raw) for a, raw in context],
    )
    crew = Crew(agents=[prod_task.agent], tasks=[task], process=Process.sequential, verbose=False)

    before = usage_counters()
    started = time.perf_counter()
    result = crew.kickoff(inputs=crew_inputs(case))
    latency = time.perf_counter() - started

    usage = usage_delta(before)
    entry = {
        "tag": tag,
        "stage": stage,
        "case_id": case["id"],
        "model": SUBJECT_MODEL,
        "latency_s": round(latency, 3),
        **usage,
        "est_cost_usd": estimate_cost(
            SUBJECT_MODEL, usage["prompt_tokens"], usage["completion_tokens"], usage["cached_tokens"]
        ),
    }
    _record(entry)
    return {"raw": result.raw, **entry}


def run_analyzer(case, tag):
    # In the API flow the analyzer's only view of the question is the output of
    # question_generation_task, so the question is injected the same way.
    return run_stage(
        "analyzer", prod_tasks.question_analysis_task, case,
        [(prod_agents.question_generator, case["question"])], tag,
    )


def run_evaluator(case, analysis_raw, tag):
    return run_stage(
        "evaluator", prod_tasks.answer_evaluation_task, case,
        [(prod_agents.question_generator, case["question"]),
         (prod_agents.question_analyzer, analysis_raw)], tag,
    )


def run_reviewer(case, evaluation_raw, tag):
    return run_stage(
        "reviewer", prod_tasks.reflection_task, case,
        [(prod_agents.answer_evaluator, evaluation_raw)], tag,
    )


def run_coach(case, analysis_raw, evaluation_raw, tag):
    # Production wiring is context=[question_analysis_task, reflection_task].
    # For the "no reviewer" arm the raw evaluator output takes the second slot.
    return run_stage(
        "coach", prod_tasks.interview_coaching_task, case,
        [(prod_agents.question_analyzer, analysis_raw),
         (prod_agents.reflection_agent, evaluation_raw)], tag,
    )


# ----------------------------------------------------------------------------
# Parsing / format checks (same assumptions as python/api.py)
# ----------------------------------------------------------------------------

def parse_like_api(raw):
    """api.py does a bare json.loads(task.raw). Returns (obj, error)."""
    try:
        return json.loads(raw), None
    except (json.JSONDecodeError, TypeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def check_evaluation_format(raw):
    obj, err = parse_like_api(raw)
    if err:
        return None, f"json.loads failed ({err})"
    try:
        EvaluationResult.model_validate(obj, strict=True)
        if type(obj.get("overallScore")) is not int:
            return obj, "overallScore missing or not an int"
    except Exception as exc:  # pydantic ValidationError
        return obj, f"schema: {str(exc).splitlines()[0]} / {str(exc).splitlines()[1].strip()}"
    return obj, None


def check_coaching_format(raw):
    obj, err = parse_like_api(raw)
    if err:
        return None, f"json.loads failed ({err})"
    try:
        CoachingResult.model_validate(obj, strict=True)
    except Exception as exc:
        return obj, f"schema: {str(exc).splitlines()[0]} / {str(exc).splitlines()[1].strip()}"
    return obj, None


def scores_of(evaluation):
    out = {k: evaluation["evaluationScores"][k]["score"] for k in SCORE_KEYS}
    out["overallScore"] = evaluation["overallScore"]
    return out


def evaluation_text(evaluation):
    """All natural-language content of an evaluation, for marker checks."""
    parts = [evaluation.get("summary", "")]
    parts += [evaluation["evaluationScores"][k]["feedback"] for k in SCORE_KEYS]
    parts += evaluation.get("strengths", []) + evaluation.get("weaknesses", [])
    return "\n".join(parts)


# ----------------------------------------------------------------------------
# LLM judges
# ----------------------------------------------------------------------------

_client = None


def judge(system, user, case_id, tag):
    """Returns {judge_model: parsed JSON verdict}. Verdicts are evidence, not truth."""
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)

    verdicts = {}
    for model in JUDGE_MODELS:
        _check_budget()
        started = time.perf_counter()
        resp = _client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        latency = time.perf_counter() - started
        cached = getattr(resp.usage.prompt_tokens_details, "cached_tokens", 0) or 0
        _record({
            "tag": tag,
            "stage": "judge",
            "case_id": case_id,
            "model": model,
            "latency_s": round(latency, 3),
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "cached_tokens": cached,
            "requests": 1,
            "est_cost_usd": estimate_cost(
                model, resp.usage.prompt_tokens, resp.usage.completion_tokens, cached
            ),
        })
        verdicts[model] = json.loads(resp.choices[0].message.content)
    return verdicts


def dump(name, data):
    path = RESULTS_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def load(name):
    return json.loads((RESULTS_DIR / name).read_text())
