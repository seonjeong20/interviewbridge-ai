"""Deterministic Validator (improvement A).

Everything here is plain code: no model call, same input -> same output.

What it checks                         What it is allowed to change
-------------------------------------  ----------------------------------------
JSON parses                            nothing (status "invalid")
schema / required fields / types       nothing (status "invalid")
each score is an int in 0..100         nothing (status "invalid")
overallScore == mean of the 5 scores   overallScore only (item scores untouched)
exact duplicate list items             removes the later copies
near-duplicate list items              nothing (reported as a hint)
identical feedback in two dimensions   nothing (reported as a hint)
same item in strengths and weaknesses  nothing (reported as a hint)

overallScore rule: python/src/tasks.py tells the Evaluator to "Calculate
overallScore as the average of logicalThinking, specificity, communication,
jobFit, and starStructure", and the API returns it as an int, so the expected
value is the arithmetic mean rounded half up.
"""

import json
import math
import re
from difflib import SequenceMatcher

from schemas import EvaluationResult

SCORE_KEYS = ["logicalThinking", "specificity", "communication", "jobFit", "starStructure"]
LIST_KEYS = ["strengths", "weaknesses"]
NEAR_DUPLICATE_RATIO = 0.8


def expected_overall(evaluation):
    mean = sum(evaluation["evaluationScores"][k]["score"] for k in SCORE_KEYS) / len(SCORE_KEYS)
    return math.floor(mean + 0.5)


def _normalize(text):
    return re.sub(r"[\s.,!?·'\"]+", "", text).lower()


def validate(raw):
    """Returns (evaluation or None, report).

    report = {"valid": bool, "errors": [...], "fixes": [...], "hints": [...]}
    The returned evaluation already has the fixes applied.
    """
    report = {"valid": False, "errors": [], "fixes": [], "hints": []}

    try:
        evaluation = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        report["errors"].append({"check": "json", "detail": f"{type(exc).__name__}: {exc}"})
        return None, report

    try:
        EvaluationResult.model_validate(evaluation, strict=True)
    except Exception as exc:
        for err in getattr(exc, "errors", lambda: [])():
            report["errors"].append({
                "check": "schema",
                "detail": f"{'.'.join(map(str, err['loc']))}: {err['msg']}",
            })
        if not report["errors"]:
            report["errors"].append({"check": "schema", "detail": str(exc)})
        return None, report

    if type(evaluation.get("overallScore")) is not int:
        report["errors"].append({"check": "schema", "detail": "overallScore: missing or not an int"})
        return None, report

    for key in SCORE_KEYS:
        score = evaluation["evaluationScores"][key]["score"]
        if not 0 <= score <= 100:
            report["errors"].append({"check": "score_range", "detail": f"{key}.score={score}"})
    if not 0 <= evaluation["overallScore"] <= 100:
        report["errors"].append({"check": "score_range",
                                 "detail": f"overallScore={evaluation['overallScore']}"})
    if report["errors"]:
        return None, report

    report["valid"] = True

    expected = expected_overall(evaluation)
    if evaluation["overallScore"] != expected:
        report["fixes"].append({
            "check": "overall_score_arithmetic",
            "field": "overallScore",
            "before": evaluation["overallScore"],
            "after": expected,
            "reason": "overallScore must equal the mean of the five item scores (rounded half up)",
        })
        evaluation["overallScore"] = expected

    for key in LIST_KEYS:
        seen, kept = {}, []
        for item in evaluation[key]:
            norm = _normalize(item)
            if norm in seen:
                report["fixes"].append({
                    "check": "exact_duplicate", "field": key, "before": item, "after": None,
                    "reason": f"identical to an earlier {key} item: {seen[norm]!r}",
                })
                continue
            seen[norm] = item
            kept.append(item)
        evaluation[key] = kept

        for i in range(len(kept)):
            for j in range(i + 1, len(kept)):
                ratio = SequenceMatcher(None, kept[i], kept[j]).ratio()
                if ratio >= NEAR_DUPLICATE_RATIO:
                    report["hints"].append({
                        "check": "near_duplicate", "field": key,
                        "items": [kept[i], kept[j]], "similarity": round(ratio, 2),
                    })

    for item in evaluation["strengths"]:
        if _normalize(item) in {_normalize(w) for w in evaluation["weaknesses"]}:
            report["hints"].append({"check": "strength_also_weakness", "item": item})

    feedbacks = {k: _normalize(evaluation["evaluationScores"][k]["feedback"]) for k in SCORE_KEYS}
    for i, a in enumerate(SCORE_KEYS):
        for b in SCORE_KEYS[i + 1:]:
            if feedbacks[a] and feedbacks[a] == feedbacks[b]:
                report["hints"].append({"check": "identical_feedback", "fields": [a, b]})

    return evaluation, report
