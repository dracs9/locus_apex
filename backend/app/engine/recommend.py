"""recommend(): filters -> fits -> score -> tier, plus suggestions when there are few results."""
from collections import defaultdict
from datetime import date, datetime, time

from app.schemas import Excluded, Profile, Reason, Recommendation, RecommendationResult, University

from . import config, text
from .interests import interest_fit
from .filters import check_budget, check_major, hard_filters
from .fit import compute_fits
from .score import achievements_factor, priority_match, score
from .tier import tier_and_chance

TIER_ORDER = {"dream": 0, "target": 1, "safety": 2}
KIND_ORDER = {"blocker": 0, "plus": 1, "risk": 2}


def _extra_pluses(profile: Profile, uni: University) -> list[Reason]:
    out = []
    fit = interest_fit(profile, uni)
    if fit is not None and fit >= 0.6:
        out.append(Reason(kind="plus", code="HOLLAND_MATCH",
            text="Выбранные направления вуза пересекаются с интересами по RIASEC",
            profile_field="holland"))
    if profile.needs_aid and uni.intl_aid.value == "full_need":
        out.append(Reason(kind="plus", code="AID_FULL_NEED", text="Даёт иностранцам полную финпомощь по потребности",
                          profile_field="needs_aid"))
    if profile.priorities.prestige >= 0.6 and uni.world_rank <= 50:
        out.append(Reason(kind="plus", code="PRESTIGE", text=f"Входит в топ-50 мирового рейтинга (#{uni.world_rank}) — это для вас важно",
                          profile_field="priorities.prestige"))
    if achievements_factor(profile) >= 0.5:
        out.append(Reason(kind="plus", code="ACHIEVEMENTS_BONUS", text="Сильные достижения выделяют заявку",
                          profile_field="achievements"))
    return out


def _sort_reasons(reasons: list[Reason]) -> list[Reason]:
    return sorted(reasons, key=lambda r: KIND_ORDER[r.kind])


def evaluate(profile: Profile, uni: University, today: date, major_names: dict[str, str]) -> Recommendation | Excluded | None:
    """None = filtered out silently (country not selected)."""
    f = hard_filters(profile, uni, major_names)
    if not f.country_ok:
        return None
    fits = compute_fits(profile, uni)
    blockers = f.blockers + [r for r in fits.reasons if r.kind == "blocker"]
    if blockers:
        return Excluded(university_id=uni.id, reasons=blockers)
    tier, chance, tier_reasons = tier_and_chance(profile, uni, fits, today)
    reasons = f.pluses + fits.reasons + _extra_pluses(profile, uni) + f.risks + tier_reasons
    return Recommendation(university_id=uni.id, tier=tier, chance=chance, score=score(profile, uni, fits),
                          priority_match=priority_match(profile, uni), reasons=_sort_reasons(reasons))


def _suggestions(profile: Profile, universities: list[University], excluded: list[Excluded],
                 major_names: dict[str, str]) -> list[str]:
    out: list[str] = []
    by_id = {u.id: u for u in universities}
    selected = [by_id[e.university_id] for e in excluded]

    over_budget = [u for u, e in zip(selected, excluded)
                   if [r.code for r in e.reasons] == ["OVER_BUDGET"]]
    if over_budget:
        if not profile.needs_aid and any(u.intl_aid.value in ("full_need", "partial") for u in over_budget):
            n = sum(u.intl_aid.value in ("full_need", "partial") for u in over_budget)
            out.append(f"Отметьте, что нужна финпомощь — откроется вузов: {n}")
        costs = sorted(u.cost_per_year_usd.value or 0 for u in over_budget)
        level = costs[min(2, len(costs) - 1)]  # budget that opens up to 3 universities
        n = sum(c <= level for c in costs)
        out.append(f"Увеличьте бюджет до {text.money(level)} в год — откроется вузов: {n}")

    ielts_blocked = [e for e in excluded if [r.code for r in e.reasons] == ["IELTS_BELOW_MIN"]]
    if ielts_blocked:
        need = min(r.gap or 0 for e in ielts_blocked for r in e.reasons)
        out.append(f"Запланируйте пересдачу IELTS (+{need:g} балла) — откроется вузов: {len(ielts_blocked)}")

    # Other countries where the student would pass major + budget filters
    by_country: dict[str, int] = defaultdict(int)
    by_major: dict[str, int] = defaultdict(int)
    for u in universities:
        budget_blockers = check_budget(profile, u)[0]
        if u.country not in profile.countries and not check_major(profile, u, major_names)[0] and not budget_blockers:
            by_country[u.country] += 1
        if u.country in profile.countries and check_major(profile, u, major_names)[0] and not budget_blockers:
            for m in u.majors:
                if m not in profile.majors:
                    by_major[m] += 1
    for c, n in sorted(by_country.items(), key=lambda kv: (-kv[1], kv[0]))[:2]:
        out.append(f"Добавьте страну «{text.country(c)}» — там подходящих вузов: {n}")
    if len(profile.majors) < 3:
        for m, n in sorted(by_major.items(), key=lambda kv: (-kv[1], kv[0]))[:1]:
            out.append(f"Добавьте направление «{major_names.get(m, m)}» — вузов: {n}")
    return out[: config.MAX_SUGGESTIONS]


def recommend(profile: Profile, universities: list[University], today: date,
              major_names: dict[str, str] | None = None) -> RecommendationResult:
    major_names = major_names or {}
    recs: list[Recommendation] = []
    excluded: list[Excluded] = []
    for uni in sorted(universities, key=lambda u: u.id):
        r = evaluate(profile, uni, today, major_names)
        if isinstance(r, Recommendation):
            recs.append(r)
        elif isinstance(r, Excluded):
            excluded.append(r)
    recs.sort(key=lambda r: (TIER_ORDER[r.tier], -r.score, r.university_id))
    suggestions = _suggestions(profile, universities, excluded, major_names) if len(recs) < 3 else []
    return RecommendationResult(recs=recs, excluded=excluded, suggestions=suggestions,
                                computed_at=datetime.combine(today, time()))
