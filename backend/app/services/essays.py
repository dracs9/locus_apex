"""Essay collection (backend/app/data/essays.json, built by pipeline/essays.py) and reading recommendations."""
import json
from functools import cache
from pathlib import Path

from app.schemas import Essay, EssaySummary, Profile, RecommendedEssay

DATA = Path(__file__).resolve().parents[1] / "data" / "essays.json"

# Recommendation weights: the audience applies to a bachelor's, so the level matters most.
W_BACHELOR = 3
W_FAVORITE = 3
W_RECOMMENDED = 2
W_MAJOR = 2
W_PERSONAL = 1   # Common App / personal statement — the formats a school student writes


@cache
def load() -> tuple[Essay, ...]:
    return tuple(Essay.model_validate(e) for e in json.loads(DATA.read_text(encoding="utf-8")))


@cache
def summaries() -> tuple[EssaySummary, ...]:
    return tuple(EssaySummary.model_validate(e.model_dump(exclude={"body", "references"})) for e in load())


def get(essay_id: str) -> Essay | None:
    return next((e for e in load() if e.id == essay_id), None)


def recommend_essays(essays: list[EssaySummary] | tuple[EssaySummary, ...], profile: Profile | None,
                     favorite_ids: list[str], rec_ids: list[str], university_names: dict[str, str],
                     major_names: dict[str, str], limit: int = 6) -> list[RecommendedEssay]:
    """Pure and deterministic: score by level, the student's universities and majors; ties broken by id."""
    favorites, recs = set(favorite_ids), set(rec_ids)
    majors = profile.majors if profile else []
    scored = []
    for e in essays:
        score, reasons = 0, []
        if e.level == "bachelor":
            score += W_BACHELOR
            reasons.append("Бакалавриат — ваш уровень поступления")
        uni = e.university_id
        if uni and uni in favorites:
            score += W_FAVORITE
            reasons.append(f"Эссе в {university_names.get(uni, e.school)} из вашего плана")
        elif uni and uni in recs:
            score += W_RECOMMENDED
            reasons.append(f"Эссе в {university_names.get(uni, e.school)} из ваших рекомендаций")
        shared = [m for m in majors if m in e.majors]
        if shared:
            score += W_MAJOR
            reasons.append("Направление: " + ", ".join(major_names.get(m, m) for m in shared))
        if e.kind in ("common_app", "personal_statement"):
            score += W_PERSONAL
        if score > 0 and reasons:
            scored.append((-score, e.id, RecommendedEssay(essay=e, reasons=reasons)))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [r for _, _, r in scored[:limit]]
