"""Offline checks for the code-only parts (no API call).

Usage: python test_offline.py
"""

import copy
import json

import v2harness  # noqa: F401
import correction
import validator

GOOD = {
    "overallScore": 60,
    "summary": "논리 전개는 좋지만 근거가 부족합니다.",
    "evaluationScores": {
        "logicalThinking": {"score": 80, "feedback": "흐름이 명확합니다."},
        "specificity": {"score": 40, "feedback": "수치가 없습니다."},
        "communication": {"score": 70, "feedback": "간결합니다."},
        "jobFit": {"score": 60, "feedback": "직무와 관련됩니다."},
        "starStructure": {"score": 50, "feedback": "행동이 부족합니다."},
    },
    "strengths": ["명확한 흐름", "간결한 전달"],
    "weaknesses": ["수치 부족", "행동 설명 부족"],
}
QUESTION, ANSWER = "경험을 말씀해 주세요.", "저는 프로젝트에서 배포를 자동화했습니다."


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


def finding(**overrides):
    base = {"issue_type": "summary_item_contradiction", "target_field": "summary",
            "problematic_text": "논리 전개는 좋지만 근거가 부족합니다.",
            "evidence_in_evaluation": ["logicalThinking.score=80"], "evidence_in_answer": [],
            "reason": "r", "action": "replace_text", "proposed_text": "근거가 부족합니다.",
            "confidence": "high"}
    return {**base, **overrides}


def test_validator():
    ev, rep = validator.validate(dumps(GOOD))
    assert rep["valid"] and not rep["fixes"] and not rep["hints"] and ev == GOOD

    assert not validator.validate("{not json")[1]["valid"]

    missing = copy.deepcopy(GOOD); del missing["weaknesses"]
    assert validator.validate(dumps(missing))[1]["errors"][0]["check"] == "schema"

    out_of_range = copy.deepcopy(GOOD); out_of_range["evaluationScores"]["jobFit"]["score"] = 130
    assert validator.validate(dumps(out_of_range))[1]["errors"][0]["check"] == "score_range"

    string_score = copy.deepcopy(GOOD); string_score["evaluationScores"]["jobFit"]["score"] = "60"
    assert not validator.validate(dumps(string_score))[1]["valid"]

    wrong_total = copy.deepcopy(GOOD); wrong_total["overallScore"] = 78
    ev, rep = validator.validate(dumps(wrong_total))
    assert ev["overallScore"] == 60 and rep["fixes"][0]["before"] == 78
    assert ev["evaluationScores"] == GOOD["evaluationScores"]  # item scores untouched

    half = copy.deepcopy(GOOD); half["evaluationScores"]["jobFit"]["score"] = 62  # mean 60.4
    assert validator.validate(dumps(half))[0]["overallScore"] == 60

    dup = copy.deepcopy(GOOD); dup["weaknesses"] = ["수치 부족", "수치 부족.", "행동 설명 부족"]
    ev, rep = validator.validate(dumps(dup))
    assert ev["weaknesses"] == ["수치 부족", "행동 설명 부족"]
    assert rep["fixes"][0]["check"] == "exact_duplicate"

    near = copy.deepcopy(GOOD); near["weaknesses"] = ["구체적인 수치가 부족함", "구체적인 수치가 부족합니다"]
    ev, rep = validator.validate(dumps(near))
    assert len(ev["weaknesses"]) == 2 and rep["hints"][0]["check"] == "near_duplicate"


def test_correction():
    apply = lambda f: correction.apply_findings(GOOD, [f], QUESTION, ANSWER)

    ev, disp, log = apply(finding())
    assert disp[0]["applied"] and ev["summary"] == "근거가 부족합니다." and len(log) == 1
    assert apply(finding(evidence_in_evaluation=["specificity.feedback=수치가 없습니다."]))[1][0]["applied"]

    for held in (
        finding(confidence="medium"),
        finding(action="flag_score"),
        finding(action="flag_only"),
        finding(problematic_text="평가에 없는 문장입니다."),
        finding(evidence_in_evaluation=["logicalThinking.score=10"]),
        finding(evidence_in_evaluation=[], evidence_in_answer=["답변에 없는 인용"]),
        finding(evidence_in_evaluation=["logicalThinking.score=80", "평가에 없는 인용"]),
        finding(evidence_in_evaluation=[]),
        finding(proposed_text="Kafka 도입으로 30% 절감했습니다."),
        finding(proposed_text=""),
        finding(proposed_text="근거가 부족합니다. " * 20),
    ):
        ev, disp, log = apply(held)
        assert not disp[0]["applied"] and ev == GOOD and not log, disp

    ev, disp, _ = apply(finding(target_field="strengths", problematic_text="간결한 전달",
                                action="remove_item", proposed_text="",
                                evidence_in_evaluation=["간결합니다."]))
    assert disp[0]["applied"] and ev["strengths"] == ["명확한 흐름"]

    single = copy.deepcopy(GOOD); single["strengths"] = ["간결한 전달"]
    ev, disp, _ = correction.apply_findings(single, [finding(
        target_field="strengths", problematic_text="간결한 전달", action="remove_item",
        proposed_text="", evidence_in_evaluation=["간결합니다."])], QUESTION, ANSWER)
    assert not disp[0]["applied"] and ev["strengths"] == ["간결한 전달"]

    # Corroboration of unsupported_by_answer without a quote: a foreign token is enough.
    kafka = copy.deepcopy(GOOD)
    kafka["evaluationScores"]["jobFit"]["feedback"] = "Kafka 운영 경험이 직무와 연결됩니다."
    ev, disp, _ = correction.apply_findings(kafka, [finding(
        issue_type="unsupported_by_answer", target_field="jobFit",
        problematic_text="Kafka 운영 경험이 직무와 연결됩니다.", evidence_in_evaluation=[],
        proposed_text="배포 자동화 경험이 직무와 연결됩니다.")], QUESTION, ANSWER)
    assert disp[0]["applied"] and "Kafka" not in ev["evaluationScores"]["jobFit"]["feedback"]

    # Scores never change; overallScore is always the recomputed mean.
    for ev in (apply(finding())[0], apply(finding(action="flag_score"))[0]):
        assert {k: v["score"] for k, v in ev["evaluationScores"].items()} == \
               {k: v["score"] for k, v in GOOD["evaluationScores"].items()}
        assert ev["overallScore"] == validator.expected_overall(ev)


if __name__ == "__main__":
    test_validator()
    test_correction()
    print("offline checks passed")
