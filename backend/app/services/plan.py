"""Changes to the student's plan, shared by the roadmap endpoints and the mentor's applied proposals."""
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import Profile, Suggestion

from . import compute, roadmap_items


class PlanError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


async def find_suggestion(session: AsyncSession, user_id: UUID, profile: Profile, suggestion_id: str) -> Suggestion:
    if suggestion_id in await roadmap_items.added_keys(session, user_id):
        raise PlanError(409, "STEP_EXISTS", "Этот шаг уже в плане")
    result = await compute.current_result(session, user_id, profile)
    s = next((s for s in await compute.suggestions_for(session, user_id, profile, result) if s.id == suggestion_id), None)
    if s is None:
        raise PlanError(404, "SUGGESTION_NOT_FOUND", "Рекомендация больше не актуальна")
    return s


async def add_from_suggestion(session: AsyncSession, user_id: UUID, profile: Profile, suggestion_id: str, *,
                              title: str | None = None, kind: str | None = None, due_date: date | None = None,
                              note: str | None = None) -> None:
    s = await find_suggestion(session, user_id, profile, suggestion_id)
    await roadmap_items.add_item(session, user_id, kind=kind or s.kind, title=title or s.title,
                                 due_date=due_date or s.suggested_due, note=note, source_key=s.id,
                                 university_ids=s.university_ids, source_url=s.source_url, is_demo=s.is_demo)


async def add_custom(session: AsyncSession, user_id: UUID, *, title: str | None, kind: str | None,
                     due_date: date | None, note: str | None = None) -> None:
    if not (title and title.strip() and kind and due_date):
        raise PlanError(422, "STEP_INCOMPLETE", "Укажите название, тип и дату шага")
    await roadmap_items.add_item(session, user_id, kind=kind, title=title.strip(), due_date=due_date, note=note)


async def patch(session: AsyncSession, user_id: UUID, item_id: UUID, values: dict) -> None:
    if any(values.get(k) is None for k in ("done", "title", "kind", "due_date") if k in values):
        raise PlanError(422, "STEP_INVALID", "Пустое значение")
    if values and not await roadmap_items.patch_item(session, user_id, item_id, values):
        raise PlanError(404, "STEP_NOT_FOUND", "Шаг не найден")


async def delete(session: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    if not await roadmap_items.delete_item(session, user_id, item_id):
        raise PlanError(404, "STEP_NOT_FOUND", "Шаг не найден")
