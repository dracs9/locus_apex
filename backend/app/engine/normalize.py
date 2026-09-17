from datetime import date

from app.schemas import Achievement, Deadline, Priorities, Profile, University

from . import config


def gpa5_to_gpa4(gpa5: float) -> float:
    table = config.GPA5_TO_GPA4
    if gpa5 <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if gpa5 <= x1:
            return round(y0 + (gpa5 - x0) * (y1 - y0) / (x1 - x0), 2)
    return table[-1][1]


def profile_gpa4(profile: Profile) -> float | None:
    record = profile.academic_record
    if record is not None:
        if record.scale == "4":
            return record.value
        if record.scale == "5":
            return gpa5_to_gpa4(record.value) if record.value >= 2 else None
        # A criterion score /8 or a percentage is not an official US GPA conversion.
        return None
    return gpa5_to_gpa4(profile.gpa5) if profile.gpa5 is not None and profile.gpa5 >= 2 else None


def toefl_to_ielts(toefl: float) -> float:
    for lower, band in config.TOEFL_TO_IELTS:
        if toefl >= lower:
            return band
    return 4.0


def done_achievements(profile: Profile) -> list[Achievement]:
    return [a for a in profile.achievements if a.status == "done"]


def best_score(profile: Profile, type_: str) -> float | None:
    scores = [a.score for a in done_achievements(profile) if a.type == type_ and a.score is not None]
    return max(scores) if scores else None


def best_ielts(profile: Profile) -> float | None:
    """Best English score on the IELTS scale (TOEFL is converted)."""
    candidates = []
    ielts = best_score(profile, "IELTS")
    if ielts is not None:
        candidates.append(ielts)
    toefl = best_score(profile, "TOEFL")
    if toefl is not None:
        candidates.append(toefl_to_ielts(toefl))
    return max(candidates) if candidates else None


def planned_exam_before(profile: Profile, types: tuple[str, ...], deadline: date) -> Achievement | None:
    planned = [a for a in profile.achievements if a.status == "planned" and a.type in types and a.date <= deadline]
    return min(planned, key=lambda a: a.date) if planned else None


def profile_at(profile: Profile, at: date) -> Profile:
    return profile.model_copy(update={"achievements": [a for a in profile.achievements if a.date <= at]})


def with_priorities(profile: Profile, priorities: Priorities | None) -> Profile:
    return profile if priorities is None else profile.model_copy(update={"priorities": priorities})


def project_deadline(d: Deadline, intake_year: int) -> date:
    """Seed deadlines are for one admission cycle. Shift them to the student's cycle:
    deadlines in Aug–Dec belong to intake next year, Jan–Jul to the same year."""
    data_intake = d.date.year + 1 if d.date.month >= 8 else d.date.year
    shift = intake_year - data_intake
    try:
        return d.date.replace(year=d.date.year + shift)
    except ValueError:  # Feb 29
        return d.date.replace(year=d.date.year + shift, day=28)


def projected_deadlines(uni: University, intake_year: int) -> list[tuple[date, Deadline, bool, str | None]]:
    """[(date, deadline, is_demo, source_url)] sorted by date.
    A verified deadline stays verified after the shift: the day and month come from the source,
    only the year moves to the student's cycle (README documents this)."""
    out = []
    for s in uni.deadlines:
        if s.value is None:
            continue
        out.append((project_deadline(s.value, intake_year), s.value, s.is_demo, s.source_url))
    return sorted(out, key=lambda t: (t[0], t[1].type))


def final_deadline(uni: University, intake_year: int) -> date | None:
    """Latest deadline of the cycle (e.g. RD / UCAS) — the last chance to apply."""
    dl = projected_deadlines(uni, intake_year)
    return dl[-1][0] if dl else None


def application_deadline(uni: University, intake_year: int, today: date):
    """Earliest deadline that has not passed yet (falls back to the latest one)."""
    dl = projected_deadlines(uni, intake_year)
    if not dl:
        return None
    for item in dl:
        if item[0] >= today:
            return item
    return dl[-1]
