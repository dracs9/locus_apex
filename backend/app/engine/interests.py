"""Original Applyra questionnaire based on Holland's six interest themes, not a Truity test."""
import json
from functools import cache
from pathlib import Path

@cache
def questionnaire():
    return json.loads((Path(__file__).parents[1] / "data/holland.json").read_text())

def scores(assessment):
    data = questionnaire()
    totals = {code: 0 for code in data["dimensions"]}
    for q in data["questions"]:
        totals[q["dimension"]] += assessment.answers[q["id"]]
    return {code: value / 20 for code, value in totals.items()}

def interest_fit(profile, uni):
    if profile.holland is None:
        return None
    values = scores(profile.holland)
    # The questionnaire refines fit only within majors explicitly chosen by the student.
    mapping = questionnaire()["major_codes"]
    matches = [m for m in profile.majors if m in uni.majors and m in mapping]
    if not matches:
        return None
    return max(sum(values[c] for c in mapping[m]) / len(mapping[m]) for m in matches)
