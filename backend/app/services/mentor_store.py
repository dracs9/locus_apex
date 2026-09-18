"""Mentor chat history. Every query is filtered by the authenticated user_id."""
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.schemas.mentor import MentorAction, MentorMessage

from .profiles import now

KEEP_LAST = 100


def _message(r) -> MentorMessage:
    return MentorMessage(id=r.id, role=r.role, text=r.text, actions=[MentorAction.model_validate(a) for a in r.actions or []],
                         generated=r.generated, created_at=r.created_at)


async def list_messages(session: AsyncSession, user_id: UUID, limit: int = KEEP_LAST) -> list[MentorMessage]:
    rows = (await session.execute(select(db.mentor_messages).where(db.mentor_messages.c.user_id == user_id)
                                  .order_by(db.mentor_messages.c.created_at.desc()).limit(limit))).all()
    return [_message(r) for r in reversed(rows)]


async def get_message(session: AsyncSession, user_id: UUID, message_id: UUID) -> MentorMessage | None:
    r = (await session.execute(select(db.mentor_messages).where(
        db.mentor_messages.c.id == message_id, db.mentor_messages.c.user_id == user_id))).first()
    return _message(r) if r else None


async def add_message(session: AsyncSession, user_id: UUID, role: str, text: str,
                      actions: list[MentorAction] | None = None, generated: bool = False) -> MentorMessage:
    msg = MentorMessage(id=uuid4(), role=role, text=text, actions=actions or [], generated=generated, created_at=now())
    await session.execute(insert(db.mentor_messages).values(
        id=msg.id, user_id=user_id, role=role, text=text, generated=generated, created_at=msg.created_at,
        actions=[a.model_dump(mode="json") for a in msg.actions]))
    old = (select(db.mentor_messages.c.id).where(db.mentor_messages.c.user_id == user_id)
           .order_by(db.mentor_messages.c.created_at.desc()).offset(KEEP_LAST).scalar_subquery())
    await session.execute(delete(db.mentor_messages).where(db.mentor_messages.c.id.in_(old)))
    return msg


async def save_actions(session: AsyncSession, user_id: UUID, message: MentorMessage) -> None:
    await session.execute(update(db.mentor_messages).where(
        db.mentor_messages.c.id == message.id, db.mentor_messages.c.user_id == user_id)
        .values(actions=[a.model_dump(mode="json") for a in message.actions]))


async def clear(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(delete(db.mentor_messages).where(db.mentor_messages.c.user_id == user_id))
