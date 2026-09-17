from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import Diff, RecommendationResult, Snapshot

KEEP_LAST = 50


def _row_to_snapshot(r) -> Snapshot:
    return Snapshot(id=r.id, at=r.at, result=RecommendationResult.model_validate(r.result),
                    roadmap_step_ids=list(r.roadmap_step_ids or []), profile_hash=r.profile_hash, cause=r.cause)


async def latest(session: AsyncSession, user_id: UUID) -> tuple[Snapshot, Diff | None] | None:
    r = (await session.execute(select(db.snapshots).where(db.snapshots.c.user_id == user_id)
                               .order_by(db.snapshots.c.at.desc()).limit(1))).first()
    if r is None:
        return None
    return _row_to_snapshot(r), (Diff.model_validate(r.diff) if r.diff else None)


async def save(session: AsyncSession, user_id: UUID, snap: Snapshot, diff: Diff | None) -> None:
    await session.execute(insert(db.snapshots).values(
        id=snap.id, user_id=user_id, at=snap.at, result=snap.result.model_dump(mode="json"),
        roadmap_step_ids=snap.roadmap_step_ids, profile_hash=snap.profile_hash, cause=snap.cause,
        diff=diff.model_dump(mode="json", by_alias=True) if diff else None))
    old = (await session.execute(select(db.snapshots.c.id).where(db.snapshots.c.user_id == user_id)
                                 .order_by(db.snapshots.c.at.desc()).offset(KEEP_LAST))).all()
    if old:
        await session.execute(delete(db.snapshots).where(db.snapshots.c.user_id == user_id,
                                                         db.snapshots.c.id.in_([r[0] for r in old])))
