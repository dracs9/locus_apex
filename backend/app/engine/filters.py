"""Hard filters (§8.2). A university with any blocker goes to `excluded`."""
from dataclasses import dataclass, field

from app.schemas import Profile, Reason, University

from . import text


@dataclass
class FilterResult:
    country_ok: bool
    blockers: list[Reason] = field(default_factory=list)
    risks: list[Reason] = field(default_factory=list)
    pluses: list[Reason] = field(default_factory=list)


def check_major(profile: Profile, uni: University, major_names: dict[str, str]) -> tuple[list[Reason], list[Reason]]:
    """Returns (blockers, pluses)."""
    matched = [m for m in profile.majors if m in uni.majors]
    if not matched:
        names = ", ".join(major_names.get(m, m) for m in profile.majors)
        return [Reason(kind="blocker", code="MAJOR_NOT_OFFERED",
                       text=f"Нет выбранного направления ({names})", profile_field="majors")], []
    names = ", ".join(major_names.get(m, m) for m in matched)
    return [], [Reason(kind="plus", code="MAJOR_MATCH", text=f"Есть ваше направление: {names}", profile_field="majors")]


def check_budget(profile: Profile, uni: University) -> tuple[list[Reason], list[Reason], list[Reason]]:
    """Returns (blockers, risks, pluses)."""
    cost = uni.cost_per_year_usd.value
    aid = uni.intl_aid.value
    budget = profile.budget_per_year_usd
    if cost is None:
        return [], [Reason(kind="risk", code="COST_UNKNOWN",
                           text="Стоимость обучения не опубликована — уточните на сайте вуза",
                           profile_field="budget_per_year_usd")], []
    if cost <= budget:
        return [], [], [Reason(kind="plus", code="WITHIN_BUDGET",
                               text=f"Стоимость {text.money(cost)}/год укладывается в ваш бюджет {text.money(budget)}",
                               profile_field="budget_per_year_usd")]
    gap = float(cost - budget)
    if not profile.needs_aid or aid in ("none", "merit_only"):
        why = "вы не отметили, что нужна финпомощь" if not profile.needs_aid else text.AID_RU[aid]
        return [Reason(kind="blocker", code="OVER_BUDGET",
                       text=f"Стоимость {text.money(cost)}/год выше бюджета на {text.money(gap)}, а {why}",
                       profile_field="budget_per_year_usd", gap=gap)], [], []
    if aid is None:  # missing data is never a blocker
        return [], [Reason(kind="risk", code="AID_UNKNOWN",
                           text=f"Дороже бюджета на {text.money(gap)}, а условия финпомощи для иностранцев не опубликованы",
                           profile_field="needs_aid", gap=gap)], []
    return [], [Reason(kind="risk", code="OVER_BUDGET_NEEDS_AID",
                       text=f"Дороже бюджета на {text.money(gap)} — всё зависит от финпомощи ({text.AID_RU[aid]})",
                       profile_field="needs_aid", gap=gap)], []


def hard_filters(profile: Profile, uni: University, major_names: dict[str, str]) -> FilterResult:
    res = FilterResult(country_ok=uni.country in profile.countries)
    blockers, pluses = check_major(profile, uni, major_names)
    res.blockers += blockers
    res.pluses += pluses
    blockers, risks, pluses = check_budget(profile, uni)
    res.blockers += blockers
    res.risks += risks
    res.pluses += pluses
    return res
