"""Essay collection (table public.essays, loaded by supabase/seed.py from supabase/seed/essays.json)
and reading recommendations. Summaries are cached in memory; full texts are read per request."""
import asyncio
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import Essay, EssaySummary, Profile, RecommendedEssay

TTL_SECONDS = 600
CORE = ("id", "university_id", "level", "kind", "word_count")
_cache: dict = {"at": 0.0, "loaded": False, "summaries": []}
_lock = asyncio.Lock()

# Recommendation weights: the audience applies to a bachelor's, so the level matters most.
W_BACHELOR = 3
W_FAVORITE = 3
W_RECOMMENDED = 2
W_MAJOR = 2
W_PERSONAL = 1   # Common App / personal statement — the formats a school student writes


def to_row(essay: Essay) -> dict:
    """Essay -> essays table row (seed.py, SQLite self-seed, tests)."""
    data = essay.model_dump(mode="json")
    row = {k: data.pop(k) for k in CORE}
    return {**row, "body": data.pop("body"), "refs": data.pop("references"), "data": data}


def _summary(row) -> EssaySummary:
    return EssaySummary.model_validate({**row.data, **{k: getattr(row, k) for k in CORE}})


def _stale() -> bool:
    return not _cache["loaded"] or time.monotonic() - _cache["at"] > TTL_SECONDS


async def summaries(session: AsyncSession) -> list[EssaySummary]:
    if _stale():
        async with _lock:
            if _stale():
                cols = [db.essays.c[k] for k in CORE] + [db.essays.c.data]
                rows = (await session.execute(select(*cols).order_by(db.essays.c.id))).all()
                _cache["summaries"] = [_summary(r) for r in rows]
                _cache["at"] = time.monotonic()
                _cache["loaded"] = True
    return _cache["summaries"]


async def get(session: AsyncSession, essay_id: str) -> Essay | None:
    row = (await session.execute(select(db.essays).where(db.essays.c.id == essay_id))).first()
    if row is None:
        return None
    return Essay.model_validate({**_summary(row).model_dump(), "body": row.body, "references": row.refs or []})


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
