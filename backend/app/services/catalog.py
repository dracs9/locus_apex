"""University / major catalog, cached in memory (read-only data, changes only on re-seed)."""
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import Major, University

TTL_SECONDS = 600
_cache: dict = {"at": 0.0, "universities": [], "majors": []}


def row_to_university(row) -> University:
    return University.model_validate({**row.data, "id": row.id, "name": row.name, "country": row.country,
                                      "city": row.city, "website": row.website, "world_rank": row.world_rank})


async def _load(session: AsyncSession) -> None:
    unis = (await session.execute(select(db.universities).order_by(db.universities.c.id))).all()
    majors = (await session.execute(select(db.majors).order_by(db.majors.c.id))).all()
    _cache["universities"] = [row_to_university(r) for r in unis]
    _cache["majors"] = [Major(id=r.id, name_ru=r.name_ru, name_en=r.name_en, cip_codes=list(r.cip_codes or []))
                        for r in majors]
    _cache["at"] = time.monotonic()


async def universities(session: AsyncSession) -> list[University]:
    if not _cache["universities"] or time.monotonic() - _cache["at"] > TTL_SECONDS:
        await _load(session)
    return _cache["universities"]


async def majors(session: AsyncSession) -> list[Major]:
    if not _cache["majors"] or time.monotonic() - _cache["at"] > TTL_SECONDS:
        await _load(session)
    return _cache["majors"]


async def major_names(session: AsyncSession) -> dict[str, str]:
    return {m.id: m.name_ru for m in await majors(session)}


def invalidate() -> None:
    _cache["at"] = 0.0
    _cache["universities"] = []
    _cache["majors"] = []
