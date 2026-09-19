"""Validate seed JSON with the backend's Pydantic models and upsert into the database.

Usage (from repo root):  backend/.venv/Scripts/python supabase/seed.py
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import asyncpg  # noqa: E402

from app.config import Settings  # noqa: E402
from app.schemas import Essay, Major, University  # noqa: E402
from app.services.essays import to_row  # noqa: E402

SEED = ROOT / "supabase" / "seed"


def load() -> tuple[list[University], list[Major]]:
    unis = [University.model_validate(u) for u in json.loads((SEED / "universities.json").read_text(encoding="utf-8"))]
    majors = [Major.model_validate(m) for m in json.loads((SEED / "majors.json").read_text(encoding="utf-8"))]
    major_ids = {m.id for m in majors}
    for u in unis:
        unknown = set(u.majors) - major_ids
        if unknown:
            sys.exit(f"{u.id}: unknown majors {unknown}")
    ids = [u.id for u in unis]
    if len(ids) != len(set(ids)):
        sys.exit("duplicate university ids")
    return unis, majors


def load_essays(majors: list[Major]) -> list[Essay]:
    essays = [Essay.model_validate(e) for e in json.loads((SEED / "essays.json").read_text(encoding="utf-8"))]
    major_ids = {m.id for m in majors}
    for e in essays:
        if set(e.majors) - major_ids:
            sys.exit(f"essay {e.id}: unknown majors {set(e.majors) - major_ids}")
    return essays


async def main() -> None:
    unis, majors = load()
    essays = load_essays(majors)
    settings = Settings(_env_file=ROOT / "backend" / ".env")
    conn = await asyncpg.connect(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
                                 statement_cache_size=0)
    try:
        async with conn.transaction():
            for m in majors:
                await conn.execute(
                    """insert into public.majors (id, name_ru, name_en, cip_codes) values ($1, $2, $3, $4)
                       on conflict (id) do update set name_ru = excluded.name_ru, name_en = excluded.name_en,
                       cip_codes = excluded.cip_codes""",
                    m.id, m.name_ru, m.name_en, m.cip_codes)
            for u in unis:
                data = u.model_dump(mode="json")
                core = {k: data.pop(k) for k in ("id", "name", "country", "city", "website", "world_rank")}
                await conn.execute(
                    """insert into public.universities (id, name, country, city, website, world_rank, data)
                       values ($1, $2, $3, $4, $5, $6, $7::jsonb)
                       on conflict (id) do update set name = excluded.name, country = excluded.country,
                       city = excluded.city, website = excluded.website, world_rank = excluded.world_rank,
                       data = excluded.data""",
                    core["id"], core["name"], core["country"], core["city"], core["website"], core["world_rank"],
                    json.dumps(data, ensure_ascii=False))
            for e in essays:
                r = to_row(e)
                await conn.execute(
                    """insert into public.essays (id, university_id, level, kind, word_count, data, body, refs)
                       values ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb)
                       on conflict (id) do update set university_id = excluded.university_id, level = excluded.level,
                       kind = excluded.kind, word_count = excluded.word_count, data = excluded.data,
                       body = excluded.body, refs = excluded.refs""",
                    r["id"], r["university_id"], r["level"], r["kind"], r["word_count"],
                    json.dumps(r["data"], ensure_ascii=False), r["body"], json.dumps(r["refs"], ensure_ascii=False))
    finally:
        await conn.close()
    demo = sum(1 for u in unis for f in (u.acceptance_rate, u.sat, u.gpa_avg, u.ielts_min, u.cost_per_year_usd, u.intl_aid)
               if f.is_demo)
    print(f"upserted {len(majors)} majors, {len(unis)} universities ({demo} demo-flagged facts), {len(essays)} essays")


if __name__ == "__main__":
    asyncio.run(main())
