"""User data access. Every query is filtered by the authenticated user_id."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas import Achievement, AchievementIn, Profile, ProfileIn


def now() -> datetime:
    return datetime.now(timezone.utc)


async def load_profile(session: AsyncSession, user_id: UUID) -> Profile | None:
    row = (await session.execute(select(db.profiles).where(db.profiles.c.user_id == user_id))).first()
    if row is None:
        return None
    rows = (await session.execute(
        select(db.achievements).where(db.achievements.c.user_id == user_id)
        .order_by(db.achievements.c.date, db.achievements.c.created_at, db.achievements.c.id))).all()
    achievements = [Achievement(id=r.id, type=r.type, score=r.score, title=r.title, level=r.level, date=r.date,
                                status=r.status) for r in rows]
    return Profile.model_validate({**row.data, "achievements": achievements})


async def save_profile(session: AsyncSession, user_id: UUID, body: ProfileIn, created_at: datetime | None) -> None:
    data = body.model_dump(mode="json", exclude={"initial_achievements"})
    data["created_at"] = (created_at or now()).isoformat()
    exists = (await session.execute(select(db.profiles.c.user_id).where(db.profiles.c.user_id == user_id))).first()
    if exists:
        await session.execute(update(db.profiles).where(db.profiles.c.user_id == user_id)
                              .values(data=data, updated_at=now()))
    else:
        await session.execute(insert(db.profiles).values(user_id=user_id, data=data, updated_at=now()))
    for a in body.initial_achievements:
        await add_achievement(session, user_id, a)


async def add_achievement(session: AsyncSession, user_id: UUID, a: AchievementIn) -> UUID:
    aid = uuid4()
    await session.execute(insert(db.achievements).values(id=aid, user_id=user_id, created_at=now(), **a.model_dump()))
    return aid


async def update_achievement(session: AsyncSession, user_id: UUID, achievement_id: UUID, values: dict) -> bool:
    res = await session.execute(update(db.achievements)
                                .where(db.achievements.c.id == achievement_id, db.achievements.c.user_id == user_id)
                                .values(**values))
    return res.rowcount > 0


async def delete_achievement(session: AsyncSession, user_id: UUID, achievement_id: UUID) -> bool:
    await session.execute(delete(db.achievement_attachments).where(
        db.achievement_attachments.c.achievement_id == achievement_id, db.achievement_attachments.c.user_id == user_id))
    res = await session.execute(delete(db.achievements)
                                .where(db.achievements.c.id == achievement_id, db.achievements.c.user_id == user_id))
    return res.rowcount > 0


async def favorite_ids(session: AsyncSession, user_id: UUID) -> list[str]:
    rows = await session.execute(select(db.favorites.c.university_id).where(db.favorites.c.user_id == user_id)
                                 .order_by(db.favorites.c.university_id))
    return [r[0] for r in rows]


async def set_favorite(session: AsyncSession, user_id: UUID, university_id: str, on: bool) -> None:
    await session.execute(delete(db.favorites).where(db.favorites.c.user_id == user_id,
                                                     db.favorites.c.university_id == university_id))
    if on:
        await session.execute(insert(db.favorites).values(user_id=user_id, university_id=university_id))


async def wipe_user(session: AsyncSession, user_id: UUID) -> None:
    for table in (db.achievement_attachments, db.achievements, db.favorites, db.roadmap_progress, db.roadmap_items,
                  db.snapshots, db.profiles):
        await session.execute(delete(table).where(table.c.user_id == user_id))
