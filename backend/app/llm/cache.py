import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.config import get_settings


def cache_key(kind: str, payload: dict) -> str:
    raw = json.dumps({"k": kind, "m": get_settings().llm_model, "p": payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


async def get(session: AsyncSession, key: str) -> dict | None:
    row = (await session.execute(select(db.llm_cache.c.value).where(db.llm_cache.c.key == key))).first()
    return row[0] if row else None


async def put(session: AsyncSession, key: str, value: dict) -> None:
    try:
        await session.execute(insert(db.llm_cache).values(key=key, value=value, created_at=datetime.now(timezone.utc)))
        await session.commit()
    except Exception:  # noqa: BLE001 — concurrent insert of the same key is fine
        await session.rollback()
