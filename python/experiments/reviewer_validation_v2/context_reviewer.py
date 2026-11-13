"""Context-Aware Reviewer (improvement B).

Differences from the production Reviewer (python/src, unchanged):
  * it receives the interview question and the candidate's answer;
  * it receives the Deterministic Validator's report;
  * it returns a list of findings, never a rewritten evaluation;
  * it cannot propose scores;
  * every finding must carry verbatim quotes so code can verify it.

Same model and temperature as production (gpt-4.1-mini, 0.3). It is called
through the OpenAI SDK with a strict response schema instead of through
crewAI, because the output must be machine-checkable.
"""

import hashlib
import json
import time
from typing import List, Literal

from pydantic import BaseModel

import v2harness  # noqa: F401  (path setup)
import harness as h

MODEL = h.SUBJECT_MODEL
TEMPERATURE = h.llm.temperature

IssueType = Literal[
    "score_feedback_contradiction",
    "summary_item_contradiction",
    "cross_item_contradiction",
    "unsupported_by_answer",
    "duplicate",
    "insufficient_grounding",
]
TargetField = Literal[
    "summary", "logicalThinking", "specificity", "communication", "jobFit", "starStructure",
    "strengths", "weaknesses",
]


class Finding(BaseModel):
    issue_type: IssueType
    target_field: TargetField
    problematic_text: str
    evidence_in_evaluation: List[str]
    evidence_in_answer: List[str]
    reason: str
    action: Literal["replace_text", "remove_item", "flag_score", "flag_only"]
    proposed_text: str
    confidence: Literal["high", "medium", "low"]


class Review(BaseModel):
    findings: List[Finding]


SYSTEM_PROMPT = """You are a quality auditor for interview-answer evaluations produced by another AI ("the Evaluator") in an interview-practice service.

You receive:
1. QUESTION - the interview question.
2. ANSWER - the candidate's answer, verbatim.
3. EVALUATION - the Evaluator's JSON: overallScore, summary, evaluationScores (logicalThinking, specificity, communication, jobFit, starStructure; each has a score from 0 to 100 and a feedback text), strengths, weaknesses.
4. VALIDATOR_REPORT - results of deterministic code checks (schema, score range, overallScore arithmetic, exact and near-duplicate list items). Schema and arithmetic are already handled by code. Do not report them.

Your job is to report defects in the EVALUATION. You do NOT re-evaluate the answer, you do NOT rewrite the evaluation, and you NEVER propose a new score.

Report only these defect types:
- score_feedback_contradiction: a score and the feedback, strength or weakness about the same dimension point in opposite directions (for example a score of 75 or more whose feedback says the dimension is missing or poor, or a score of 45 or less while a strength praises that same dimension).
- summary_item_contradiction: the summary states something that an item score, an item feedback, a strength or a weakness contradicts.
- cross_item_contradiction: two parts of the evaluation state opposite facts about the answer (for example one says figures were given and another says no figures were given).
- unsupported_by_answer: the evaluation cites as fact something that is not in the ANSWER (a technology, a number, an achievement, a behaviour, or a property such as "long" or "short" that the ANSWER plainly does not have).
- duplicate: two items in the same list (strengths or weaknesses) make the same point.
- insufficient_grounding: the evaluation is so generic that it refers to nothing in the ANSWER.

These are NOT defects and must not be reported: wording or style; a score you find strict or lenient; dimensions having very different scores; a strength and a weakness about different aspects; the same weakness being reflected in the feedback of several dimensions; anything you would simply have evaluated differently.

Deciding which side of a contradiction is wrong: check the ANSWER. The side that the ANSWER does not support is the defective one. If the text is right and the score is the side that is wrong, use action "flag_score".

For each finding return:
- issue_type
- target_field: the field that contains the defective text.
- problematic_text: copied character for character from that field. For strengths or weaknesses copy the entire list item. For summary or feedback copy the whole defective sentence (the whole field only if it is a single sentence).
- evidence_in_evaluation: a list of the other parts of the evaluation that expose the problem. Each entry is either one passage copied character for character, or one score written exactly like specificity.score=90. One quote or one score per entry; do not add labels. Empty list if not applicable.
- evidence_in_answer: a list of passages of the ANSWER, each copied character for character, that show what is true. Empty list when the point is that the ANSWER contains nothing of the kind.
- reason: one or two sentences, in the language of the evaluation.
- action: "replace_text" (replace problematic_text with proposed_text), "remove_item" (delete this strengths or weaknesses item), "flag_score" (the score looks wrong; someone else must decide), or "flag_only" (cannot be fixed without re-evaluating; use this for insufficient_grounding).
- proposed_text: only for replace_text, otherwise an empty string. A minimal rewrite of problematic_text in the same language and tone. It may only remove the false claim, or restate it using facts that are literally in the ANSWER or elsewhere in the EVALUATION. Never add a new fact, number, technology or judgement.
- confidence: "high" only if the quotes you give make the defect checkable without further judgement; otherwise "medium" or "low".

For duplicates: keep the clearest item and return one remove_item finding for each of the other items, with the item you keep as the evidence_in_evaluation entry.

If the evaluation has none of these defects, return an empty findings list. Most evaluations have none; an empty list is a normal and correct result."""

PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()

_client = None


def review(question, answer, evaluation, validator_report, case_id, tag, stage="context_reviewer"):
    """One LLM call. Returns (findings as list of dicts, ledger entry)."""
    global _client
    h._check_budget()
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=h.OPENAI_API_KEY)

    user = (
        "QUESTION:\n" + question
        + "\n\nANSWER:\n" + answer
        + "\n\nEVALUATION:\n" + json.dumps(evaluation, ensure_ascii=False, indent=2)
        + "\n\nVALIDATOR_REPORT:\n" + json.dumps(validator_report, ensure_ascii=False, indent=2)
    )
    started = time.perf_counter()
    resp = _client.chat.completions.parse(
        model=MODEL,
        temperature=TEMPERATURE,
        response_format=Review,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
    )
    latency = time.perf_counter() - started

    cached = getattr(resp.usage.prompt_tokens_details, "cached_tokens", 0) or 0
    entry = {
        "tag": tag, "stage": stage, "case_id": case_id, "model": MODEL,
        "latency_s": round(latency, 3),
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "cached_tokens": cached, "requests": 1,
        "est_cost_usd": h.estimate_cost(MODEL, resp.usage.prompt_tokens,
                                        resp.usage.completion_tokens, cached),
    }
    h._record(entry)
    parsed = resp.choices[0].message.parsed
    return [f.model_dump() for f in parsed.findings], entry
