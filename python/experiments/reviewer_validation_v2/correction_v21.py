"""Controlled Correction, revision 2.1 (ID-based).

Plain code. Gates, fixed before v2.1 was run on any test case:

  G0 the reviewer's own claim_check does not say the target piece is supported
     by the answer (a self-consistency check on the model's output)
  G1 defective_side is "text", action is replace_text or remove_item, and
     confidence is "high". A "score" finding is never applied: this stage
     cannot change item scores. It is kept as a score flag only if it passes
     S1, otherwise it is dismissed.
  S1 a score flag must cite a piece that the reviewer's claim_check does not
     mark as unsupported and that points the other way under the thresholds
     given in the prompt: says "negative" with score >= 75, or says "positive"
     with score <= 45
  G2 target_id is an existing text piece; remove_item only on list items
  G3 only evidence ids that exist count; unknown ids and the target itself are ignored
  G4 there is at least one evidence id, or, for unsupported_by_answer, the
     piece contains a number / Latin token absent from question and answer
  G5 proposed_text adds no number or Latin token that is not in the question,
     the answer or the piece it replaces (unsupported_by_answer: question and
     answer only)
  G6 proposed_text is non-empty and not much longer than the piece
  G7 a removal never leaves strengths or weaknesses empty
  D1 duplicate group: keep_id and remove_ids are items of the same list
  S2 score flags are also derived by code from the claim_check, without relying
     on the model to report them: a feedback sentence of dimension d that the
     reviewer classified as "negative" (and not unsupported) while d's score is
     >= 75, or "positive" while d's score is <= 45

overallScore is recomputed by code after the edits.
"""

import copy

from correction import GENERIC_LATIN, _tokens
from validator import SCORE_KEYS, expected_overall


HIGH_SCORE, LOW_SCORE = 75, 45


def expand(ref, ids):
    """Human-readable form of an id, for the log."""
    if ref in ids["A"]:
        return f"{ref} [answer] {ids['A'][ref]}"
    if ref in ids["S"]:
        return f"{ref} [{ids['S'][ref]['field']}.score] {ids['S'][ref]['score']}"
    if ref in ids["P"]:
        return f"{ref} [{ids['P'][ref]['field']}] {ids['P'][ref]['text']}"
    return f"{ref} [unknown id]"


def decide(finding, review, ids, question, answer, list_sizes):
    target = finding["target_id"]
    if finding["defective_side"] == "score":
        score = ids["S"].get(target, {}).get("score")
        claims = {c["id"]: c for c in review["claim_check"]}
        for ref in finding["evidence_ids"]:
            claim = claims.get(ref)
            if score is None or claim is None or claim["supported_by_answer"] == "no":
                continue
            if (claim["says"] == "negative" and score >= HIGH_SCORE) or \
               (claim["says"] == "positive" and score <= LOW_SCORE):
                return False, "G1 score flag: item scores are never changed by this stage"
        return False, "S1 dismissed: no cited piece points the other way from this score"
    if finding["action"] not in ("replace_text", "remove_item"):
        return False, f"G1 action is {finding['action']}"
    if finding["confidence"] != "high":
        return False, f"G1 confidence is {finding['confidence']}"
    if target not in ids["P"]:
        return False, "G2 target_id is not a text piece"
    piece = ids["P"][target]
    if finding["action"] == "remove_item" and piece["list_index"] is None:
        return False, "G2 remove_item is only valid for strengths/weaknesses items"

    claim = next((c for c in review["claim_check"] if c["id"] == target), None)
    if claim is not None and claim["supported_by_answer"] == "yes":
        return False, "G0 the reviewer's own claim_check says the answer supports this piece"

    known = set(ids["A"]) | set(ids["S"]) | set(ids["P"])
    evidence = [e for e in finding["evidence_ids"] if e != target and e in known]

    context_tokens = _tokens(question) | _tokens(answer) | GENERIC_LATIN
    if not evidence:
        foreign = _tokens(piece["text"]) - context_tokens
        if not (finding["issue_type"] == "unsupported_by_answer" and foreign):
            return False, "G4 no evidence for this finding"

    if finding["action"] == "replace_text":
        proposed = finding["proposed_text"].strip()
        if not proposed:
            return False, "G6 proposed_text is empty"
        if len(proposed) > max(2 * len(piece["text"]), len(piece["text"]) + 60):
            return False, "G6 proposed_text is much longer than the piece it replaces"
        allowed = set(context_tokens)
        if finding["issue_type"] != "unsupported_by_answer":
            allowed |= _tokens(piece["text"])
        added = _tokens(proposed) - allowed
        if added:
            return False, f"G5 proposed_text introduces unverified tokens: {sorted(added)}"
    elif list_sizes[piece["field"]] <= 1:
        return False, "G7 removal would leave the list empty"

    return True, "all gates passed"


def apply_review(evaluation, review, ids, question, answer):
    """Returns (corrected evaluation, annotated findings, annotated duplicate groups, change_log)."""
    corrected = copy.deepcopy(evaluation)
    scores_before = {k: corrected["evaluationScores"][k]["score"] for k in SCORE_KEYS}
    list_sizes = {f: len(corrected[f]) for f in ("strengths", "weaknesses")}
    replacements, removals, change_log = {}, set(), []

    findings = []
    for finding in review["findings"]:
        ok, reason = decide(finding, review, ids, question, answer, list_sizes)
        target = finding["target_id"]
        if ok and (target in replacements or target in removals):
            ok, reason = False, "an earlier finding already edited this piece"
        findings.append({
            **finding, "applied": ok, "gate_result": reason,
            "target_field": (ids["P"].get(target) or ids["S"].get(target) or {}).get("field"),
            "target_text": expand(target, ids),
            "evidence_text": [expand(e, ids) for e in finding["evidence_ids"]],
        })
        if not ok:
            continue
        piece = ids["P"][target]
        if finding["action"] == "remove_item":
            removals.add(target)
            list_sizes[piece["field"]] -= 1
            after = None
        else:
            after = finding["proposed_text"].strip()
            replacements[target] = after
        change_log.append({"source": "context_reviewer", "field": piece["field"],
                           "issue_type": finding["issue_type"], "before": piece["text"],
                           "after": after, "reason": finding["reason"]})

    groups = []
    for group in review["duplicate_groups"]:
        members = [group["keep_id"], *group["remove_ids"]]
        pieces = [ids["P"].get(m) for m in members]
        valid = (all(p is not None and p["list_index"] is not None for p in pieces)
                 and len({p["field"] for p in pieces}) == 1
                 and group["keep_id"] not in group["remove_ids"] and group["remove_ids"])
        removed = []
        if valid:
            field = pieces[0]["field"]
            for rid in group["remove_ids"]:
                if rid in removals or rid in replacements or list_sizes[field] <= 1:
                    continue
                removals.add(rid)
                list_sizes[field] -= 1
                removed.append(rid)
                change_log.append({"source": "context_reviewer", "field": field,
                                   "issue_type": "duplicate", "before": ids["P"][rid]["text"],
                                   "after": None,
                                   "reason": f"same point as: {ids['P'][group['keep_id']]['text']}"})
        groups.append({**group, "applied": bool(removed),
                       "target_field": pieces[0]["field"] if valid else None,
                       "gate_result": "D1 passed" if valid else "D1 ids are not items of one list",
                       "keep_text": expand(group["keep_id"], ids),
                       "remove_text": [expand(r, ids) for r in group["remove_ids"]]})

    # S2: score conflicts that follow mechanically from the claim_check.
    score_ids = {v["field"]: k for k, v in ids["S"].items()}
    flagged = {f["target_id"] for f in findings
               if f["defective_side"] == "score" and f["gate_result"].startswith("G1")}
    for claim in review["claim_check"]:
        piece = ids["P"].get(claim["id"])
        if piece is None or piece["field"] not in score_ids or claim["supported_by_answer"] == "no":
            continue
        sid = score_ids[piece["field"]]
        score = ids["S"][sid]["score"]
        if sid in flagged or claim["id"] in replacements:
            continue
        if (claim["says"] == "negative" and score >= HIGH_SCORE) or \
           (claim["says"] == "positive" and score <= LOW_SCORE):
            flagged.add(sid)
            findings.append({
                "issue_type": "score_feedback_contradiction", "target_id": sid,
                "defective_side": "score", "evidence_ids": [claim["id"]],
                "reason": f"derived by code: feedback classified as {claim['says']} while the score is {score}",
                "action": "none", "proposed_text": "", "confidence": "high",
                "applied": False,
                "gate_result": "G1 score flag: item scores are never changed by this stage (S2 derived)",
                "target_field": piece["field"],
                "target_text": expand(sid, ids), "evidence_text": [expand(claim["id"], ids)],
            })

    # Rebuild the text fields from the pieces.
    def rebuild(field):
        parts = [replacements.get(pid, p["text"]) for pid, p in ids["P"].items()
                 if p["field"] == field and pid not in removals]
        return parts

    corrected["summary"] = " ".join(rebuild("summary"))
    for key in SCORE_KEYS:
        corrected["evaluationScores"][key]["feedback"] = " ".join(rebuild(key))
    for field in ("strengths", "weaknesses"):
        corrected[field] = rebuild(field)

    assert scores_before == {k: corrected["evaluationScores"][k]["score"] for k in SCORE_KEYS}
    corrected["overallScore"] = expected_overall(corrected)
    return corrected, findings, groups, change_log
