"""The student's own plan steps. Every query is filtered by the authenticated user_id."""
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import RoadmapStep

from .profiles import now


def _step(r) -> RoadmapStep:
    return RoadmapStep(id=str(r.id), kind=r.kind, title=r.title, due_date=r.due_date, depends_on=[],
                       university_ids=list(r.university_ids or []), source_url=r.source_url, is_demo=r.is_demo,
                       done=r.done, priority=0, source_key=r.source_key, note=r.note)


async def list_items(session: AsyncSession, user_id: UUID) -> list[RoadmapStep]:
    rows = await session.execute(select(db.roadmap_items).where(db.roadmap_items.c.user_id == user_id)
                                 .order_by(db.roadmap_items.c.due_date, db.roadmap_items.c.created_at))
    return [_step(r) for r in rows]


async def added_keys(session: AsyncSession, user_id: UUID) -> set[str]:
    rows = await session.execute(select(db.roadmap_items.c.source_key).where(
        db.roadmap_items.c.user_id == user_id, db.roadmap_items.c.source_key.is_not(None)))
    return {r[0] for r in rows}


async def add_item(session: AsyncSession, user_id: UUID, *, kind: str, title: str, due_date: date,
                   note: str | None = None, source_key: str | None = None, university_ids: list[str] | None = None,
                   source_url: str | None = None, is_demo: bool = False) -> UUID:
    item_id = uuid4()
    await session.execute(insert(db.roadmap_items).values(
        id=item_id, user_id=user_id, kind=kind, title=title, due_date=due_date, note=note, source_key=source_key,
        university_ids=university_ids or [], source_url=source_url, is_demo=is_demo, done=False, done_at=None,
        created_at=now()))
    return item_id


async def patch_item(session: AsyncSession, user_id: UUID, item_id: UUID, values: dict) -> bool:
    if "done" in values:
        values["done_at"] = now() if values["done"] else None
    res = await session.execute(update(db.roadmap_items)
                                .where(db.roadmap_items.c.id == item_id, db.roadmap_items.c.user_id == user_id)
                                .values(**values))
    return res.rowcount > 0


async def delete_item(session: AsyncSession, user_id: UUID, item_id: UUID) -> bool:
    res = await session.execute(delete(db.roadmap_items)
                                .where(db.roadmap_items.c.id == item_id, db.roadmap_items.c.user_id == user_id))
    return res.rowcount > 0
