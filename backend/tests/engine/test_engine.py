from datetime import date, datetime, timedelta
from uuid import uuid4

from app.engine.diff import describe_changes, diff
from app.engine.history import chance_history
from app.engine.normalize import gpa5_to_gpa4, profile_at, project_deadline
from app.engine.recommend import recommend
from app.engine.roadmap import build_roadmap, detect_conflicts, next_step
from app.schemas import Deadline, RoadmapStep, Snapshot

from .conftest import TODAY, ach, make_profile, make_uni


def rec_of(result, uid):
    return next((r for r in result.recs if r.university_id == uid), None)


def excluded_of(result, uid):
    return next((e for e in result.excluded if e.university_id == uid), None)


# --- normalization ---------------------------------------------------------

def test_gpa_conversion_table_and_interpolation():
    assert gpa5_to_gpa4(5.0) == 4.0
    assert gpa5_to_gpa4(4.5) == 3.5
    assert gpa5_to_gpa4(3.0) == 2.0
    assert gpa5_to_gpa4(4.25) == 3.25


def test_deadline_projection_to_intake_year():
    d = Deadline(type="RD", date=date(2027, 1, 15))
    assert project_deadline(d, 2028) == date(2028, 1, 15)
    ed = Deadline(type="ED", date=date(2026, 11, 1))
    assert project_deadline(ed, 2027) == date(2026, 11, 1)
    assert project_deadline(ed, 2029) == date(2028, 11, 1)


def test_profile_at_filters_by_date():
    p = make_profile(achievements=[ach("SAT", 1300, on=date(2026, 1, 1)), ach("SAT", 1500, on=date(2026, 8, 1))])
    assert len(profile_at(p, date(2026, 3, 1)).achievements) == 1


# --- §8.9 required tests ---------------------------------------------------

def test_determinism():
    unis = [make_uni("a"), make_uni("b", acceptance_rate={"value": 0.05, "is_demo": True}), make_uni("c", country="UK")]
    p = make_profile()
    assert recommend(p, unis, TODAY).model_dump() == recommend(p, unis, TODAY).model_dump()
    assert recommend(p, list(reversed(unis)), TODAY).model_dump() == recommend(p, unis, TODAY).model_dump()


def test_raising_sat_above_p25_moves_dream_to_target():
    uni = make_uni("u", acceptance_rate={"value": 0.2, "is_demo": True})
    low = make_profile(achievements=[ach("SAT", 1350), ach("IELTS", 7.0)])
    high = make_profile(achievements=[ach("SAT", 1350), ach("SAT", 1420), ach("IELTS", 7.0)])
    assert rec_of(recommend(low, [uni], TODAY), "u").tier == "dream"
    assert rec_of(recommend(high, [uni], TODAY), "u").tier == "target"


def test_lowering_budget_excludes_no_aid_university():
    uni = make_uni("u", cost_per_year_usd={"value": 40000, "is_demo": True}, intl_aid={"value": "none", "is_demo": True})
    rich = recommend(make_profile(budget_per_year_usd=50000), [uni], TODAY)
    poor = recommend(make_profile(budget_per_year_usd=20000, needs_aid=True), [uni], TODAY)
    assert rec_of(rich, "u") is not None
    assert rec_of(poor, "u") is None
    assert "OVER_BUDGET" in [r.code for r in excluded_of(poor, "u").reasons]


def test_over_budget_with_full_need_aid_is_risk_not_blocker():
    uni = make_uni("u", intl_aid={"value": "full_need", "is_demo": True})
    res = recommend(make_profile(budget_per_year_usd=10000, needs_aid=True), [uni], TODAY)
    assert "OVER_BUDGET_NEEDS_AID" in [r.code for r in rec_of(res, "u").reasons]


def test_changing_major_changes_set():
    unis = [make_uni("cs_school", majors=["cs"]), make_uni("bio_school", majors=["biology"])]
    a = {r.university_id for r in recommend(make_profile(majors=["cs"]), unis, TODAY).recs}
    b = {r.university_id for r in recommend(make_profile(majors=["biology"]), unis, TODAY).recs}
    assert a == {"cs_school"} and b == {"bio_school"}
    excluded = recommend(make_profile(majors=["cs"]), unis, TODAY).excluded
    assert excluded[0].reasons[0].code == "MAJOR_NOT_OFFERED"


def test_country_not_selected_is_silently_filtered():
    res = recommend(make_profile(countries=["UK"]), [make_uni("us")], TODAY)
    assert res.recs == [] and res.excluded == []


def test_selective_university_is_never_safety():
    uni = make_uni("elite", acceptance_rate={"value": 0.05, "is_demo": True},
                   sat={"value": {"p25": 1200, "p75": 1300}, "is_demo": True}, gpa_avg={"value": 3.0, "is_demo": True})
    star = make_profile(gpa5=5.0, achievements=[ach("SAT", 1600), ach("IELTS", 9.0)])
    r = rec_of(recommend(star, [uni], TODAY), "elite")
    assert r.tier == "dream" and r.chance == "medium"


def test_safety_when_all_fits_and_accessible():
    uni = make_uni("easy", acceptance_rate={"value": 0.6, "is_demo": True})
    r = rec_of(recommend(make_profile(), [uni], TODAY), "easy")
    assert (r.tier, r.chance) == ("safety", "high")


def test_planned_achievements_do_not_affect_scoring():
    uni = make_uni("u")
    base = make_profile()
    planned = make_profile(achievements=base.achievements + [ach("SAT", 1600, status="planned"),
                                                              ach("OLYMPIAD", level="international", status="planned")])
    a, b = recommend(base, [uni], TODAY), recommend(planned, [uni], TODAY)
    assert a.recs[0].tier == b.recs[0].tier and a.recs[0].score == b.recs[0].score
    assert a.recs[0].reasons == b.recs[0].reasons


def test_missing_data_never_produces_blocker():
    empty = {"value": None, "is_demo": True}
    uni = make_uni("unknown", acceptance_rate=empty, sat=empty, gpa_avg=empty, ielts_min=empty,
                   cost_per_year_usd=empty, intl_aid=empty, deadlines=[])
    for p in (make_profile(), make_profile(achievements=[], budget_per_year_usd=0, needs_aid=True)):
        res = recommend(p, [uni], TODAY)
        assert res.excluded == []
        assert all(r.kind != "blocker" for r in res.recs[0].reasons)
        assert "DATA_NOT_PUBLISHED" in [r.code for r in res.recs[0].reasons]
    # over budget with unknown aid policy is a risk too
    uni2 = make_uni("aidless", intl_aid=empty)
    res = recommend(make_profile(budget_per_year_usd=1000, needs_aid=True), [uni2], TODAY)
    assert res.excluded == []


def test_ielts_below_min_is_blocker_unless_retake_planned():
    uni = make_uni("u")
    p = make_profile(achievements=[ach("SAT", 1450), ach("IELTS", 5.5)])
    assert excluded_of(recommend(p, [uni], TODAY), "u").reasons[0].code == "IELTS_BELOW_MIN"
    p2 = make_profile(achievements=p.achievements + [ach("IELTS", status="planned", on=date(2026, 11, 1))])
    r = rec_of(recommend(p2, [uni], TODAY), "u")
    assert r is not None and r.tier == "dream"


def test_every_recommendation_has_two_reasons():
    unis = [make_uni("a"), make_uni("b", country="UK", sat={"value": None, "is_demo": True}),
            make_uni("c", acceptance_rate={"value": 0.05, "is_demo": True})]
    for r in recommend(make_profile(), unis, TODAY).recs:
        assert len(r.reasons) >= 2


def test_suggestions_when_few_results():
    unis = [make_uni(f"u{i}", cost_per_year_usd={"value": 30000 + i * 1000, "is_demo": True}) for i in range(4)]
    unis.append(make_uni("nl", country="NL", cost_per_year_usd={"value": 15000, "is_demo": True}))
    res = recommend(make_profile(budget_per_year_usd=20000, countries=["US"]), unis, TODAY)
    assert len(res.recs) == 0
    assert any("бюджет" in s for s in res.suggestions)
    assert any("Нидерланды" in s for s in res.suggestions)


# --- diff ------------------------------------------------------------------

def snap(result, step_ids=(), cause="c"):
    return Snapshot(id=uuid4(), at=datetime(2026, 9, 17), result=result, roadmap_step_ids=list(step_ids),
                    profile_hash="h", cause=cause)


def test_diff_reports_changes():
    unis = [make_uni("a", acceptance_rate={"value": 0.2, "is_demo": True}, cost_per_year_usd={"value": 25000, "is_demo": True}), make_uni("cheap", cost_per_year_usd={"value": 20000, "is_demo": True}),
            make_uni("pricey", cost_per_year_usd={"value": 45000, "is_demo": True})]
    before_p = make_profile(budget_per_year_usd=50000, achievements=[ach("SAT", 1350), ach("IELTS", 7.0)])
    after_p = make_profile(budget_per_year_usd=30000, achievements=[ach("SAT", 1420), ach("IELTS", 7.0)])
    before, after = recommend(before_p, unis, TODAY), recommend(after_p, unis, TODAY)
    d = diff(snap(before, ["exam:SAT"]), snap(after, ["apply:a:RD"], cause=describe_changes(before_p, after_p)))
    assert d.removed == ["pricey"]
    assert d.added == []
    assert [(t.id, t.from_, t.to) for t in d.tier_changed] == [("a", "dream", "target"), ("cheap", "dream", "target")]
    assert {"id": "a", "code": "SAT_BELOW_P25"} in [g.model_dump() for g in d.gaps_closed]
    assert d.roadmap_added == ["apply:a:RD"] and d.roadmap_removed == ["exam:SAT"]
    assert "Бюджет" in d.cause and "SAT 1350 → 1420" in d.cause
    assert diff(None, snap(after)) is None
    assert d.model_dump(by_alias=True)["tier_changed"][0]["from"] == "dream"


# --- roadmap ---------------------------------------------------------------

def test_roadmap_steps_are_deterministic_and_progress_survives():
    uni = make_uni("u", sat={"value": {"p25": 1500, "p75": 1580}, "is_demo": True})
    p = make_profile()
    recs = recommend(p, [uni], TODAY).recs
    r1 = build_roadmap(p, [], recs, [uni], {}, TODAY)
    ids = [s.id for s in r1.steps]
    assert {"exam:SAT", "exam:SAT:register", "doc:transcript", "doc:essay", "apply:u:RD"} <= set(ids)
    r2 = build_roadmap(p, [], recs, [uni], {"exam:SAT:register": True}, TODAY)
    assert [s.id for s in r2.steps] == ids
    assert r2.progress > 0
    assert r2.next_step_id != "exam:SAT:register"
    apply = next(s for s in r1.steps if s.id == "apply:u:RD")
    assert "exam:SAT" in apply.depends_on and apply.due_date == date(2027, 1, 15)


def test_roadmap_uses_favorites_first():
    a, b = make_uni("a"), make_uni("b")
    p = make_profile()
    recs = recommend(p, [a, b], TODAY).recs
    rm = build_roadmap(p, ["b"], recs, [a, b], {}, TODAY)
    assert {s.id for s in rm.steps if s.kind == "application"} == {"apply:b:RD"}


def test_conflict_when_exam_result_arrives_after_deadline():
    deadline = TODAY + timedelta(days=5)
    steps = [
        RoadmapStep(id="exam:IELTS", kind="exam", title="Сдать IELTS", due_date=TODAY - timedelta(days=10), depends_on=[],
                    university_ids=["u"], is_demo=True, done=False, priority=4),
        RoadmapStep(id="apply:u:RD", kind="application", title="Подать", due_date=deadline, depends_on=["exam:IELTS"],
                    university_ids=["u"], is_demo=True, done=False, priority=5),
    ]
    conflicts = detect_conflicts(steps, TODAY)
    assert [c.step_id for c in conflicts] == ["exam:IELTS"]
    assert next_step(steps).id == "exam:IELTS"
    steps[0].done = True
    assert detect_conflicts(steps, TODAY) == []


# --- chance history --------------------------------------------------------

def test_chance_history_follows_achievements():
    uni = make_uni("u", acceptance_rate={"value": 0.2, "is_demo": True})
    p = make_profile(created_at=datetime(2026, 1, 1), achievements=[
        ach("IELTS", 7.0, on=date(2026, 1, 1)), ach("SAT", 1300, on=date(2026, 3, 1)), ach("SAT", 1450, on=date(2026, 8, 1))])
    hist = chance_history(p, ["u"], [uni])
    assert [h.date for h in hist] == [date(2026, 1, 1), date(2026, 3, 1), date(2026, 8, 1)]
    assert hist[1].chance_by_uni["u"] == "low" and hist[2].chance_by_uni["u"] == "medium"
    assert hist[2].achievement_id is not None


def test_roadmap_demo_flags_follow_deadline_source():
    verified = make_uni("real", deadlines=[{"value": {"type": "RD", "date": "2025-01-05"}, "is_demo": False,
                                            "source_url": "https://example.edu/cds.pdf"}])
    demo = make_uni("demo")
    p = make_profile(intake_year=2028)
    for uni, expected in ((verified, False), (demo, True)):
        rm = build_roadmap(p, [uni.id], recommend(p, [uni], TODAY).recs, [uni], {}, TODAY)
        apply = next(s for s in rm.steps if s.kind == "application")
        doc = next(s for s in rm.steps if s.id == "doc:essay")
        assert apply.due_date == (date(2028, 1, 5) if uni.id == "real" else date(2028, 1, 15))
        assert apply.is_demo is expected and doc.is_demo is expected
