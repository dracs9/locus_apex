"""Score (§8.4): weighted sum of factors in 0..1, reported as 0..100 (ranking only, never shown as a chance)."""
from app.schemas import Profile, University

from . import config
from .fit import Fits
from .normalize import done_achievements
from .interests import interest_fit


def academic_factor(fits: Fits) -> float:
    values = [config.FIT_VALUE[f] for f in fits.academic()]
    return sum(values) / len(values) if values else config.UNKNOWN_FACTOR


def language_factor(fits: Fits) -> float:
    return config.LANGUAGE_VALUE.get(fits.ielts, config.UNKNOWN_FACTOR)


def major_factor(profile: Profile, uni: University) -> float:
    fit = interest_fit(profile, uni)
    if fit is not None:
        return fit

    if profile.majors[0] in uni.majors:  # the first major is the main one
        return 1.0
    return 0.7 if any(m in uni.majors for m in profile.majors) else 0.0


def affordability_factor(profile: Profile, uni: University) -> float:
    cost = uni.cost_per_year_usd.value
    if cost is None:
        return config.UNKNOWN_FACTOR
    if cost <= profile.budget_per_year_usd:
        return 1.0
    return {"full_need": 0.7, "partial": 0.4}.get(uni.intl_aid.value or "none", 0.0)


def priority_values(profile: Profile, uni: University) -> dict[str, float]:
    cost = uni.cost_per_year_usd.value
    if cost is None:
        cost_v = config.UNKNOWN_FACTOR
    else:
        cost_v = 1.0 if cost <= 0 else min(1.0, profile.budget_per_year_usd / cost)
    aid = uni.intl_aid.value
    return {
        "cost": cost_v,
        "prestige": max(0.0, 1 - (uni.world_rank - 1) / config.PRESTIGE_RANK_FLOOR),
        "aid": config.AID_VALUE[aid] if aid else config.UNKNOWN_FACTOR,
        "location": 1.0 if uni.country == profile.countries[0] else 0.5,
    }


def priorities_factor(profile: Profile, uni: University) -> float:
    p = profile.priorities.model_dump()
    total = sum(p.values())
    if total == 0:
        return config.UNKNOWN_FACTOR
    values = priority_values(profile, uni)
    return sum(p[k] * values[k] for k in values) / total


def achievements_factor(profile: Profile) -> float:
    bonus = sum(config.LEVEL_BONUS.get(a.level or "school", 0.1)
                for a in done_achievements(profile) if a.type in config.ACTIVITY_TYPES)
    return min(1.0, bonus)


def score(profile: Profile, uni: University, fits: Fits) -> float:
    w = config.WEIGHTS
    total = (w["academic"] * academic_factor(fits)
             + w["language"] * language_factor(fits)
             + w["major"] * major_factor(profile, uni)
             + w["affordability"] * affordability_factor(profile, uni)
             + w["priorities"] * priorities_factor(profile, uni)
             + w["achievements"] * achievements_factor(profile))
    return round(total * 100, 1)
