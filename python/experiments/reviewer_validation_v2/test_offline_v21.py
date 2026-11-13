"""Offline checks for the v2.1 code-only parts (no API call).

Usage: python test_offline_v21.py
"""

import v2harness  # noqa: F401
import context_reviewer_v21 as reviewer
import correction_v21 as correction
from test_offline import ANSWER, GOOD, QUESTION

IDS = reviewer.index_evaluation(GOOD, ANSWER)
# P1 summary, P2..P6 feedback, P7-P8 strengths, P9-P10 weaknesses; S1..S5; A1
assert list(IDS["P"]) == [f"P{i}" for i in range(1, 11)] and IDS["P"]["P7"]["field"] == "strengths"


def claims(**overrides):
    base = {pid: {"id": pid, "says": "neutral", "supported_by_answer": "unclear", "conflicts_with": []}
            for pid in IDS["P"]}
    for pid, change in overrides.items():
        base[pid].update(change)
    return list(base.values())


def finding(**overrides):
    base = {"issue_type": "summary_item_contradiction", "target_id": "P1", "defective_side": "text",
            "evidence_ids": ["S2", "A1"], "reason": "r", "action": "replace_text",
            "proposed_text": "근거가 부족합니다.", "confidence": "high"}
    return {**base, **overrides}


def run(findings=(), groups=(), claim_check=None):
    review = {"claim_check": claim_check or claims(), "findings": list(findings),
              "duplicate_groups": list(groups)}
    return correction.apply_review(GOOD, review, IDS, QUESTION, ANSWER)


def scores(ev):
    return {k: v["score"] for k, v in ev["evaluationScores"].items()}


ev, fs, _, log = run([finding()])
assert fs[0]["applied"] and ev["summary"] == "근거가 부족합니다." and len(log) == 1

# Nothing to do -> identical evaluation.
assert run()[0] == GOOD

for held in (
    finding(confidence="medium"),
    finding(action="none"),
    finding(target_id="P99"),
    finding(target_id="S2"),                      # text finding must target a piece
    finding(evidence_ids=[]),                     # G4
    finding(evidence_ids=["P1", "S77"]),          # only the target and an unknown id
    finding(proposed_text="Kafka 도입으로 30% 절감했습니다."),
    finding(proposed_text=""),
    finding(action="remove_item"),                # summary is not a list item
):
    ev, fs, _, log = run([held])
    assert not fs[0]["applied"] and ev == GOOD and not log, fs[0]["gate_result"]

# G0: the model's own claim check says the answer supports the piece.
ev, fs, _, _ = run([finding()], claim_check=claims(P1={"supported_by_answer": "yes"}))
assert not fs[0]["applied"] and fs[0]["gate_result"].startswith("G0")

# Score findings are never applied and scores never move.
ev, fs, _, _ = run([finding(target_id="S2", defective_side="score", action="none", evidence_ids=["P3"])])
assert not fs[0]["applied"] and fs[0]["gate_result"].startswith("S1") and scores(ev) == scores(GOOD)

# S2: a negative, not-unsupported feedback under a high score is flagged by code.
high = {**GOOD, "evaluationScores": {**GOOD["evaluationScores"],
                                     "specificity": {"score": 90, "feedback": "수치가 없습니다."}}}
ids_high = reviewer.index_evaluation(high, ANSWER)
review = {"claim_check": claims(P3={"says": "negative", "supported_by_answer": "yes"}),
          "findings": [], "duplicate_groups": []}
ev, fs, _, log = correction.apply_review(high, review, ids_high, QUESTION, ANSWER)
assert len(fs) == 1 and fs[0]["target_id"] == "S2" and not log and scores(ev) == scores(high)

# Duplicate groups: same list only, list never emptied.
ev, _, gs, _ = run(groups=[{"keep_id": "P9", "remove_ids": ["P10"]}])
assert gs[0]["applied"] and ev["weaknesses"] == ["수치 부족"]
ev, _, gs, _ = run(groups=[{"keep_id": "P7", "remove_ids": ["P9"]}])
assert not gs[0]["applied"] and ev == GOOD
ev, _, gs, _ = run(groups=[{"keep_id": "P7", "remove_ids": ["P7", "P8"]}])
assert not gs[0]["applied"] and ev == GOOD

print("offline v2.1 checks passed")
