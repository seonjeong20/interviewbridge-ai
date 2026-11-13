"""Definitions fixed before any v2 run on the test cases (see PREREGISTRATION.md)."""

# Where the planted defect lives. A run counts as "detected" when the pipeline
# produced a finding on one of these fields (whether or not it was applied),
# or, for arithmetic cases, when the validator logged the overallScore fix.
DEFECT_FIELDS = {
    "TC-07": ["summary"],
    "TC-08": ["specificity"],
    "TC-09": ["strengths"],
    "TC-10": ["jobFit"],
    "TC-11": ["communication"],
    "TC-12": "insufficient_grounding",
    "TC-13": ["specificity", "jobFit", "strengths", "summary"],
    "TC-14": ["weaknesses"],
    "TC-15": ["strengths", "weaknesses"],
    "TC-16": ["summary"],
    "TC-17": "validator_overall",
    "HO-03": ["summary"],
    "HO-04": ["communication"],
    "HO-05": ["specificity", "jobFit", "strengths", "summary"],
    "HO-06": ["strengths"],
    "HO-07": "validator_overall",
    "HO-08": ["weaknesses"],
}


def detected(case_id, run):
    where = DEFECT_FIELDS.get(case_id)
    if where is None:
        return None
    if where == "validator_overall":
        return any(f["check"] == "overall_score_arithmetic" for f in run["validator_report"]["fixes"])
    if where == "insufficient_grounding":
        return any(f["issue_type"] == "insufficient_grounding" for f in run["findings"])
    # v2.1 reports duplicates as groups; they count as findings on that list.
    found = run["findings"] + run.get("duplicate_groups", [])
    return any(f.get("target_field") in where for f in found)
