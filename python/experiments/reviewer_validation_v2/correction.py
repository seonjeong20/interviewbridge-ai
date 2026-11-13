"""Controlled Correction (improvement C).

Plain code. Takes the reviewer's findings and decides, finding by finding,
whether the edit may be applied. A finding is applied only if every gate
below passes; otherwise it is held and the evaluation is marked needs_review.

Gates (fixed before the experiments were run):
  G1 confidence is "high" and action is replace_text or remove_item
     (flag_score / flag_only are never applied: scores are never edited here)
  G2 problematic_text is found verbatim in the target field
  G3 every evidence quote that is given (one or more per finding) is found verbatim in its source
     (answer text, evaluation text, or a `dim.score=N` that matches)
  G4 the finding is corroborated: at least one verified evidence quote, or,
     for unsupported_by_answer, the flagged text contains a number or Latin
     token that is absent from the question and answer
  G5 proposed_text adds no number or Latin token that is not in the question,
     the answer or the text being replaced (unsupported_by_answer: question
     and answer only)
  G6 proposed_text is non-empty and not much longer than what it replaces
  G7 remove_item does not leave strengths or weaknesses empty

overallScore is never taken from a model: it is recomputed by the validator.
"""

import copy
import re

from validator import SCORE_KEYS, expected_overall

NUMBER = re.compile(r"\d+(?:\.\d+)?")
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9+#]+")
GENERIC_LATIN = {"star"}
SCORE_EVIDENCE = re.compile(r"^(\w+)\.score\s*=\s*(\d+)$")
# The model sometimes prefixes a quote with the field it came from
# ("specificity.feedback=..."). The label is dropped before matching.
FIELD_LABEL = re.compile(r"^(?:summary|strengths|weaknesses|\w+\.feedback)(?:\[\d+\])?\s*[=:]\s*", re.S)


def _squash(text):
    return " ".join(text.split())


def _tokens(text):
    return set(NUMBER.findall(text)) | {t.lower() for t in LATIN.findall(text)}


def evaluation_texts(evaluation):
    texts = [evaluation["summary"]]
    texts += [evaluation["evaluationScores"][k]["feedback"] for k in SCORE_KEYS]
    texts += evaluation["strengths"] + evaluation["weaknesses"]
    return texts


def _evidence_in_evaluation_ok(quote, evaluation):
    match = SCORE_EVIDENCE.match(quote.strip())
    if match:
        dim, value = match.group(1), int(match.group(2))
        if dim == "overallScore":
            return evaluation["overallScore"] == value
        return dim in SCORE_KEYS and evaluation["evaluationScores"][dim]["score"] == value
    quote = FIELD_LABEL.sub("", quote.strip(), count=1)
    return any(_squash(quote) in _squash(t) for t in evaluation_texts(evaluation))


def _locate(evaluation, field, quote):
    """Returns a (getter, setter/remover) description or None."""
    quote = quote.strip()
    if field == "summary":
        return ("text", None) if quote and quote in evaluation["summary"] else None
    if field in SCORE_KEYS:
        return ("text", None) if quote and quote in evaluation["evaluationScores"][field]["feedback"] else None
    for index, item in enumerate(evaluation[field]):
        if quote and (quote == item.strip() or quote in item):
            return ("list", index)
    return None


def _read(evaluation, field):
    if field == "summary":
        return evaluation["summary"]
    return evaluation["evaluationScores"][field]["feedback"]


def _write(evaluation, field, value):
    if field == "summary":
        evaluation["summary"] = value
    else:
        evaluation["evaluationScores"][field]["feedback"] = value


def decide(finding, evaluation, question, answer):
    """Returns (apply: bool, reason: str)."""
    if finding["action"] in ("flag_score", "flag_only"):
        return False, f"G1 action {finding['action']} is never auto-applied"
    if finding["confidence"] != "high":
        return False, f"G1 confidence is {finding['confidence']}"
    if finding["action"] == "remove_item" and finding["target_field"] not in ("strengths", "weaknesses"):
        return False, "G1 remove_item is only valid for strengths/weaknesses"

    located = _locate(evaluation, finding["target_field"], finding["problematic_text"])
    if located is None:
        return False, "G2 problematic_text not found verbatim in the target field"

    verified = 0
    quotes = [q for q in finding["evidence_in_evaluation"] if q.strip()]
    if quotes:
        if not all(_evidence_in_evaluation_ok(q, evaluation) for q in quotes):
            return False, "G3 evidence_in_evaluation not found in the evaluation"
        verified += 1
    quotes = [q for q in finding["evidence_in_answer"] if q.strip()]
    if quotes:
        if not all(_squash(q) in _squash(answer) for q in quotes):
            return False, "G3 evidence_in_answer not found in the answer"
        verified += 1

    context_tokens = _tokens(question) | _tokens(answer) | GENERIC_LATIN
    if verified == 0:
        foreign = _tokens(finding["problematic_text"]) - context_tokens
        if not (finding["issue_type"] == "unsupported_by_answer" and foreign):
            return False, "G4 no verifiable evidence for this finding"

    if finding["action"] == "replace_text":
        proposed = finding["proposed_text"].strip()
        original = finding["problematic_text"].strip()
        if not proposed:
            return False, "G6 proposed_text is empty"
        if len(proposed) > max(2 * len(original), len(original) + 60):
            return False, "G6 proposed_text is much longer than the text it replaces"
        allowed = set(context_tokens)
        if finding["issue_type"] != "unsupported_by_answer":
            allowed |= _tokens(original)
        added = _tokens(proposed) - allowed
        if added:
            return False, f"G5 proposed_text introduces unverified tokens: {sorted(added)}"
    else:
        if len(evaluation[finding["target_field"]]) <= 1:
            return False, "G7 removal would leave the list empty"

    return True, "all gates passed"


def apply_findings(evaluation, findings, question, answer):
    """Returns (corrected evaluation, dispositions, change_log).

    Item scores are never modified. overallScore is recomputed from them.
    """
    corrected = copy.deepcopy(evaluation)
    scores_before = {k: corrected["evaluationScores"][k]["score"] for k in SCORE_KEYS}
    dispositions, change_log = [], []

    for finding in findings:
        ok, reason = decide(finding, corrected, question, answer)
        dispositions.append({"applied": ok, "gate_result": reason})
        if not ok:
            continue

        field, quote = finding["target_field"], finding["problematic_text"].strip()
        kind, index = _locate(corrected, field, quote)
        if kind == "text":
            before = _read(corrected, field)
            after = before.replace(quote, finding["proposed_text"].strip(), 1)
            _write(corrected, field, after)
        elif finding["action"] == "remove_item":
            before = corrected[field][index]
            after = None
            del corrected[field][index]
        else:
            before = corrected[field][index]
            after = before.replace(quote, finding["proposed_text"].strip(), 1)
            corrected[field][index] = after
        change_log.append({
            "source": "context_reviewer", "field": field, "issue_type": finding["issue_type"],
            "before": before, "after": after, "reason": finding["reason"],
        })

    assert scores_before == {k: corrected["evaluationScores"][k]["score"] for k in SCORE_KEYS}
    corrected["overallScore"] = expected_overall(corrected)
    return corrected, dispositions, change_log
