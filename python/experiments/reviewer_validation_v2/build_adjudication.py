"""Writes ai_assisted_adjudication.json.

The verdicts below were assigned by the AI coding agent that ran this
experiment, by reading each final evaluation / coaching output. They are NOT
human review. This script only attaches the decisive text from the stored
outputs to each verdict so that every one of them can be re-checked.

Verdict vocabulary is the one used in v1 (resolved / partial / not_resolved /
preserved / no_grounding_added), plus:
  modified  - a defect-free evaluation whose content was changed (a valid item
              removed or a true statement weakened)
For the answer-dependent cases (TC-13, HO-05) resolved / partial / not_resolved
describe whether the facts that are not in the answer were removed.
"""

import json

import v2harness
import harness as h

R, P, N, OK, MOD, NG = "resolved", "partial", "not_resolved", "preserved", "modified", "no_grounding_added"


def per_rep(default, n, **exceptions):
    out = {i: default for i in range(1, n + 1)}
    for verdict, reps in exceptions.items():
        for rep in reps:
            out[rep] = {"R": R, "P": P, "N": N, "OK": OK, "MOD": MOD}[verdict]
    return out


MAIN = {
    "v20": {
        **{c: per_rep(OK, 5) for c in ("TC-01", "TC-02", "TC-03", "TC-04", "TC-05")},
        "TC-06": per_rep(OK, 5, MOD=[1, 2]),
        "TC-07": per_rep(N, 5, R=[1]), "TC-08": per_rep(N, 5), "TC-09": per_rep(N, 5, R=[1]),
        "TC-10": per_rep(N, 5), "TC-11": per_rep(N, 5, R=[3]), "TC-12": per_rep(NG, 5),
        "TC-13": per_rep(N, 5, R=[2], P=[3, 4]),
        "TC-14": per_rep(P, 5, R=[3, 5]), "TC-15": per_rep(R, 5, P=[2]),
        "TC-16": per_rep(N, 5), "TC-17": per_rep(R, 5),
    },
    "v21": {
        "TC-01": per_rep(MOD, 5), "TC-02": per_rep(OK, 5), "TC-03": per_rep(OK, 5, MOD=[1]),
        "TC-04": per_rep(OK, 5), "TC-05": per_rep(OK, 5), "TC-06": per_rep(MOD, 5, OK=[2]),
        "TC-07": per_rep(R, 5, N=[4]), "TC-08": per_rep(N, 5), "TC-09": per_rep(P, 5),
        "TC-10": per_rep(N, 5, R=[3, 4]), "TC-11": per_rep(R, 5), "TC-12": per_rep(NG, 5),
        "TC-13": per_rep(R, 5), "TC-14": per_rep(R, 5), "TC-15": per_rep(R, 5, P=[1]),
        "TC-16": per_rep(P, 5, R=[1, 3]), "TC-17": per_rep(R, 5),
    },
}
HELDOUT = {
    "production_reviewer": {
        "HO-01": per_rep(OK, 3), "HO-02": per_rep(OK, 3), "HO-03": per_rep(N, 3),
        "HO-04": per_rep(N, 3), "HO-05": per_rep(N, 3), "HO-06": per_rep(R, 3),
        "HO-07": per_rep(N, 3), "HO-08": per_rep(R, 3, P=[2]),
    },
    "v20": {
        "HO-01": per_rep(OK, 3), "HO-02": per_rep(OK, 3), "HO-03": per_rep(R, 3, N=[2]),
        "HO-04": per_rep(N, 3), "HO-05": per_rep(P, 3), "HO-06": per_rep(R, 3),
        "HO-07": per_rep(R, 3), "HO-08": per_rep(R, 3, P=[3]),
    },
    "v21": {
        "HO-01": per_rep(OK, 3), "HO-02": per_rep(OK, 3), "HO-03": per_rep(R, 3),
        "HO-04": per_rep(N, 3), "HO-05": per_rep(R, 3, P=[3]), "HO-06": per_rep(R, 3),
        "HO-07": per_rep(R, 3), "HO-08": per_rep(R, 3),
    },
}
# Does the coaching (summary + tips; for TC-13 also the model answer) carry the planted error?
COACH_CARRIES = {
    "A_no_reviewer": {"TC-07": [1, 2, 3], "TC-11": [1], "TC-13": [1, 2, 3], "TC-16": [1]},
    "B_production_reviewer": {"TC-07": [1], "TC-13": [1, 2, 3]},
    "C_improved": {"TC-13": [1, 2, 3]},
    "D_improved_v21": {},
}
COACH_CASES = ["TC-07", "TC-08", "TC-09", "TC-10", "TC-11", "TC-13", "TC-16"]

DECISIVE = {
    "TC-07": lambda o: "summary: " + o["summary"],
    "TC-08": lambda o: f"specificity.score={o['evaluationScores']['specificity']['score']} / feedback: "
                       + o["evaluationScores"]["specificity"]["feedback"],
    "TC-09": lambda o: "strengths: " + json.dumps(o["strengths"], ensure_ascii=False),
    "TC-10": lambda o: "jobFit feedback: " + o["evaluationScores"]["jobFit"]["feedback"],
    "TC-11": lambda o: "communication: " + o["evaluationScores"]["communication"]["feedback"]
                       + " / starStructure: " + o["evaluationScores"]["starStructure"]["feedback"],
    "TC-12": lambda o: "summary: " + o["summary"],
    "TC-13": lambda o: "specificity: " + o["evaluationScores"]["specificity"]["feedback"] + " / jobFit: "
                       + o["evaluationScores"]["jobFit"]["feedback"] + " / strengths: "
                       + json.dumps(o["strengths"], ensure_ascii=False),
    "TC-14": lambda o: "weaknesses: " + json.dumps(o["weaknesses"], ensure_ascii=False),
    "TC-15": lambda o: "strengths: " + json.dumps(o["strengths"], ensure_ascii=False) + " / weaknesses: "
                       + json.dumps(o["weaknesses"], ensure_ascii=False),
    "TC-16": lambda o: "summary: " + o["summary"] + " / weaknesses: "
                       + json.dumps(o["weaknesses"], ensure_ascii=False),
    "TC-17": lambda o: f"overallScore={o['overallScore']} (five-item mean 58)",
    "HO-03": lambda o: "summary: " + o["summary"],
    "HO-04": lambda o: "communication: " + o["evaluationScores"]["communication"]["feedback"],
    "HO-05": lambda o: "specificity: " + o["evaluationScores"]["specificity"]["feedback"] + " / jobFit: "
                       + o["evaluationScores"]["jobFit"]["feedback"] + " / strengths: "
                       + json.dumps(o["strengths"], ensure_ascii=False),
    "HO-06": lambda o: "strengths: " + json.dumps(o["strengths"], ensure_ascii=False),
    "HO-07": lambda o: f"overallScore={o['overallScore']} (five-item mean 66)",
    "HO-08": lambda o: "weaknesses: " + json.dumps(o["weaknesses"], ensure_ascii=False),
}
NOTES = {
    ("v21", "TC-09"): "모순된 강점은 사라졌지만, 삭제 대신 치환되어 비판 문장이 strengths 목록에 들어감",
    ("v21", "TC-16"): "'수치로 제시'는 사라짐. partial은 '구체적으로 제시/설명'으로만 완화된 경우. 일부 실행은 별개의 약점 1개가 중복으로 삭제됨",
    ("v21", "TC-13"): "답변에 없는 Kafka, Airflow, 30%는 모두 제거됨. 구체성 85점, 직무 적합성 85점은 그대로",
    ("v20", "TC-08"): "점수 불일치를 지적했으나 점수는 바꾸지 않도록 설계되어 보류",
    ("v21", "TC-08"): "점수 불일치를 지적했으나 점수는 바꾸지 않도록 설계되어 보류",
    ("v21", "HO-05"): "답변에 없는 AWS 경력과 자격증 주장은 제거됨. partial은 '자격증 여부는 언급되지 않았다'는 문장이 strengths에 들어간 경우. 점수 80, 90은 그대로",
}


def evidence(case_id, final_raw, change_log=None):
    obj = json.loads(final_raw)
    if case_id in DECISIVE:
        return DECISIVE[case_id](obj)
    removed = [c["before"] for c in (change_log or []) if c["source"] != "validator"]
    return ("변경 내역: " + json.dumps(removed, ensure_ascii=False)) if removed else "변경 없음 또는 의미 유지"


def main():
    out = {
        "_label": "AI-assisted adjudication",
        "_note": "Verdicts assigned by the AI coding agent that ran the experiment, by reading the outputs. "
                 "Not reviewed by a person. Each verdict carries the decisive text.",
        "main": {}, "heldout": {}, "coach": {},
    }
    sources = {"v20": "e1_main_runs.json", "v21": "e1_main_runs_v21.json"}
    for version, name in sources.items():
        for r in h.load(name):
            verdict = MAIN[version][r["case_id"]][r["rep"]]
            note = NOTES.get((version, r["case_id"]), "")
            out["main"][f"{version}|{r['case_id']}#{r['rep']}"] = {
                "verdict": verdict, "note": note,
                "evidence": evidence(r["case_id"], r["final_raw"], r["pipeline"]["change_log"])}

    for name, default_version in (("e4_heldout_runs.json", "v20"), ("e4_heldout_runs_v21.json", "v21")):
        for r in h.load(name):
            arm = "production_reviewer" if r["arm"] == "production_reviewer" else default_version
            out["heldout"][f"{arm}|{r['case_id']}#{r['rep']}"] = {
                "verdict": HELDOUT[arm][r["case_id"]][r["rep"]],
                "note": NOTES.get((arm, r["case_id"]), ""),
                "evidence": evidence(r["case_id"], r["final_raw"],
                                     r.get("pipeline", {}).get("change_log"))}

    for r in h.load("e2_coach_runs.json"):
        if r["case_id"] not in COACH_CASES:
            continue
        carries = r["rep"] in COACH_CARRIES[r["arm"]].get(r["case_id"], [])
        coaching = json.loads(r["coach_raw"])
        if r["case_id"] == "TC-13":
            answer = coaching["modelAnswer"]["nativeLanguage"]
            found = [k for k in ("Kafka", "Airflow", "30%") if k in answer]
            text = "모범 답안에 포함: " + (", ".join(found) if found else "없음")
            assert bool(found) == carries, (r["arm"], r["rep"])
        else:
            text = "overallSummary: " + coaching["overallSummary"][:220]
        out["coach"][f"{r['arm']}|{r['case_id']}#{r['rep']}"] = {"carries_error": carries, "evidence": text}

    (v2harness.V2_DIR / "ai_assisted_adjudication.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print(len(out["main"]), len(out["heldout"]), len(out["coach"]))


if __name__ == "__main__":
    main()
