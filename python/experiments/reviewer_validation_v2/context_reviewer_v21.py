"""Context-Aware Reviewer, revision 2.1.

Written after the frozen v2.0 run on the 17 original cases (results/e1_main_runs.json).
What v2.0 got wrong and what changed here:

  v2.0 failure (17-case run)                         change in v2.1
  -------------------------------------------------  -----------------------------------------
  quotes failed verification because the model       the code numbers every sentence / item /
  added labels, quote marks or bare field names      score / answer sentence; the model refers
  (11 findings held at gate G3)                      to IDs, so there is nothing to mis-quote
  the model chose "flag_score" although the text     the model states which side the ANSWER
  was the wrong side (TC-07, TC-10, TC-11)           contradicts; the action follows from that
  false positive on a defect-free evaluation         a claim-check step comes first; a piece the
  (TC-06, 5/5) and a missed summary clause (TC-16)   ANSWER supports can never be the defect
  duplicate lists only partly merged (TC-14)         duplicates are returned as groups

Model and temperature are unchanged (production settings).
"""

import hashlib
import json
import re
import time
from typing import List, Literal

from pydantic import BaseModel

import v2harness  # noqa: F401
import harness as h
from validator import SCORE_KEYS

MODEL = h.SUBJECT_MODEL
TEMPERATURE = h.llm.temperature

SENTENCE_END = re.compile(r"(?<=[.!?。])\s+")


class ClaimCheck(BaseModel):
    id: str
    says: Literal["positive", "negative", "mixed", "neutral"]
    supported_by_answer: Literal["yes", "no", "unclear"]
    conflicts_with: List[str]


class Finding(BaseModel):
    issue_type: Literal[
        "score_feedback_contradiction", "summary_item_contradiction", "cross_item_contradiction",
        "unsupported_by_answer", "insufficient_grounding",
    ]
    target_id: str
    defective_side: Literal["text", "score"]
    evidence_ids: List[str]
    reason: str
    action: Literal["replace_text", "remove_item", "none"]
    proposed_text: str
    confidence: Literal["high", "medium", "low"]


class DuplicateGroup(BaseModel):
    keep_id: str
    remove_ids: List[str]


class Review(BaseModel):
    claim_check: List[ClaimCheck]
    findings: List[Finding]
    duplicate_groups: List[DuplicateGroup]


SYSTEM_PROMPT = """You are a quality auditor for interview-answer evaluations produced by another AI ("the Evaluator") in an interview-practice service.

You receive:
- QUESTION: the interview question.
- ANSWER: the candidate's answer, split into numbered sentences A1, A2, ...
- SCORES: the Evaluator's scores (0 to 100), numbered S1 to S5, one per dimension.
- TEXT: every piece of the Evaluator's text, numbered P1, P2, ... Each piece is one sentence of the summary, one sentence of a dimension's feedback, one strengths item or one weaknesses item. The field it belongs to is shown in brackets.
- VALIDATOR_REPORT: results of deterministic code checks. Schema and overallScore arithmetic are already handled by code. Do not report them.

You report defects in the evaluation. You do NOT re-evaluate the answer, you do NOT rewrite the evaluation, and you NEVER propose a score.

STEP 1 - claim_check. Return one entry for EVERY piece P1..Pn:
- id
- says: "positive" if the piece praises the answer, "negative" if it criticises it, "mixed" if both, "neutral" if neither.
- supported_by_answer: "yes" if the ANSWER bears out what the piece claims about the answer; "no" if the ANSWER shows the claim to be false or contains nothing of the kind the piece cites; "unclear" if it is a matter of judgement.
  Be literal. "No experience was described" is supported when the ANSWER describes none. "Figures were given" is not supported when the ANSWER has no figures. "The answer is long" is not supported when the ANSWER is a few short sentences.
- conflicts_with: the IDs (P.. or S..) of other parts of the evaluation that say the opposite about the same thing. A positive piece conflicts with a low score (45 or less) of the dimension it is about; a negative piece conflicts with a high score (75 or more) of the dimension it is about. Empty list if nothing conflicts.

STEP 2 - findings. Report a finding only where STEP 1 found a problem, that is, a piece with supported_by_answer "no", or a piece with a non-empty conflicts_with. For every conflict decide which side is defective by checking the ANSWER: the side the ANSWER does not support is the defective one. A piece that the ANSWER supports is never the defective side. A score is the defective side in one situation only: a piece that the ANSWER supports points the opposite way from the score of the dimension it is about (a negative piece with a score of 75 or more, or a positive piece with a score of 45 or less). A score that points the same way as its feedback is never a finding.

These are NOT defects and must not be reported: wording or style; a score you find strict or lenient; dimensions having very different scores; a strength and a weakness about different aspects of the answer; the same weakness being reflected in the feedback of several dimensions; anything you would simply have evaluated differently.

Each finding has:
- issue_type: score_feedback_contradiction (a score and a piece about the same dimension point in opposite directions), summary_item_contradiction (a summary sentence is contradicted by a score, feedback, strength or weakness), cross_item_contradiction (two pieces state opposite facts about the answer), unsupported_by_answer (a piece cites as fact something that is not in the ANSWER), insufficient_grounding (the evaluation is so generic that it refers to nothing in the ANSWER).
- defective_side: "text" if a piece is wrong, "score" if a score is wrong.
- target_id: the P-id of the defective piece when defective_side is "text"; the S-id of the score when it is "score".
- evidence_ids: the IDs, other than target_id, that prove it: the conflicting P/S ids, and the A ids of the ANSWER sentences that show what is true. Leave out A ids only when the point is that the ANSWER contains nothing of the kind.
- reason: one or two sentences in the language of the evaluation.
- action: for defective_side "text": "replace_text" or, for a strengths/weaknesses item that should simply go, "remove_item". Use "none" for defective_side "score" and for insufficient_grounding.
- proposed_text: for replace_text only, otherwise an empty string. It replaces the whole piece. Write a minimal rewrite in the same language and tone that removes the false claim, or restates it using only facts that are literally in the ANSWER or in other pieces. Never add a new fact, number, technology or judgement.
- confidence: "high" only if the evidence_ids make the defect checkable without further judgement; otherwise "medium" or "low".

STEP 3 - duplicate_groups. If several items of the SAME list (strengths or weaknesses) make the same point, return one group per point: keep_id is the clearest item, remove_ids are all the others that repeat it. Items about different points are not duplicates.

If the evaluation has no defects, findings and duplicate_groups are empty lists. Most evaluations have none; that is a normal and correct result."""

PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()


def split_sentences(text):
    return [s for s in SENTENCE_END.split(text.strip()) if s]


def index_evaluation(evaluation, answer):
    """Assigns IDs. Returns {"A": {...}, "S": {...}, "P": {...}} with P entries
    as {"field", "list_index" (lists only), "text"}."""
    ids = {"A": {}, "S": {}, "P": {}}
    for i, sentence in enumerate(split_sentences(answer), 1):
        ids["A"][f"A{i}"] = sentence
    for i, key in enumerate(SCORE_KEYS, 1):
        ids["S"][f"S{i}"] = {"field": key, "score": evaluation["evaluationScores"][key]["score"]}

    n = 0
    def add(field, text, list_index=None):
        nonlocal n
        n += 1
        ids["P"][f"P{n}"] = {"field": field, "list_index": list_index, "text": text}

    for sentence in split_sentences(evaluation["summary"]):
        add("summary", sentence)
    for key in SCORE_KEYS:
        for sentence in split_sentences(evaluation["evaluationScores"][key]["feedback"]):
            add(key, sentence)
    for field in ("strengths", "weaknesses"):
        for index, item in enumerate(evaluation[field]):
            add(field, item, index)
    return ids


def render(question, ids, validator_report):
    lines = ["QUESTION:", question, "", "ANSWER:"]
    lines += [f"{k}: {v}" for k, v in ids["A"].items()]
    lines += ["", "SCORES:"]
    lines += [f"{k}: {v['field']} = {v['score']}" for k, v in ids["S"].items()]
    lines += ["", "TEXT:"]
    for k, v in ids["P"].items():
        label = v["field"] if v["field"] in ("summary", "strengths", "weaknesses") else f"{v['field']} feedback"
        lines.append(f"{k} [{label}]: {v['text']}")
    lines += ["", "VALIDATOR_REPORT:", json.dumps(validator_report, ensure_ascii=False)]
    return "\n".join(lines)


_client = None


def review(question, answer, evaluation, validator_report, case_id, tag, stage="context_reviewer"):
    """One LLM call. Returns (review dict, ids, ledger entry)."""
    global _client
    h._check_budget()
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=h.OPENAI_API_KEY)

    ids = index_evaluation(evaluation, answer)
    started = time.perf_counter()
    resp = _client.chat.completions.parse(
        model=MODEL, temperature=TEMPERATURE, response_format=Review,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": render(question, ids, validator_report)}],
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
    return resp.choices[0].message.parsed.model_dump(), ids, entry
