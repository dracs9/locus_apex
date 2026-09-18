from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import ComputeResponse, Roadmap, StepIn, StepPatch, Suggestion
from app.services import catalog, compute, ics, profiles, roadmap_items

router = APIRouter(prefix="/me", tags=["roadmap"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "STEP_NOT_FOUND", "message": "Шаг не найден"})


@router.get("/roadmap", response_model=Roadmap)
async def get_roadmap(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    await compute.require_profile(session, user_id)
    return await compute.roadmap_for(session, user_id)


@router.get("/roadmap/suggestions", response_model=list[Suggestion])
async def get_suggestions(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    """What the engine recommends adding to the plan (steps already added are left out)."""
    profile = await compute.require_profile(session, user_id)
    result = await compute.current_result(session, user_id, profile)
    return await compute.suggestions_for(session, user_id, profile, result)


@router.post("/roadmap/items", response_model=Roadmap, status_code=201)
async def add_step(body: StepIn, user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    if body.suggestion_id:
        if body.suggestion_id in await roadmap_items.added_keys(session, user_id):
            raise HTTPException(status_code=409, detail={"code": "STEP_EXISTS", "message": "Этот шаг уже в плане"})
        result = await compute.current_result(session, user_id, profile)
        s = next((s for s in await compute.suggestions_for(session, user_id, profile, result)
                  if s.id == body.suggestion_id), None)
        if s is None:
            raise HTTPException(status_code=404, detail={"code": "SUGGESTION_NOT_FOUND",
                                                         "message": "Рекомендация больше не актуальна"})
        await roadmap_items.add_item(session, user_id, kind=body.kind or s.kind, title=body.title or s.title,
                                     due_date=body.due_date or s.suggested_due, note=body.note, source_key=s.id,
                                     university_ids=s.university_ids, source_url=s.source_url, is_demo=s.is_demo)
    else:
        if not (body.title and body.kind and body.due_date):
            raise HTTPException(status_code=422, detail={"code": "STEP_INCOMPLETE",
                                                         "message": "Укажите название, тип и дату шага"})
        await roadmap_items.add_item(session, user_id, kind=body.kind, title=body.title.strip(),
                                     due_date=body.due_date, note=body.note)
    await session.commit()
    return await compute.roadmap_for(session, user_id)


@router.patch("/roadmap/items/{item_id}", response_model=Roadmap)
async def patch_step(item_id: UUID, body: StepPatch, user_id: UUID = Depends(get_user_id),
                     session: AsyncSession = Depends(get_session)):
    values = body.model_dump(exclude_unset=True)
    if any(values.get(k) is None for k in ("done", "title", "kind", "due_date") if k in values):
        raise HTTPException(status_code=422, detail={"code": "STEP_INVALID", "message": "Пустое значение"})
    if values and not await roadmap_items.patch_item(session, user_id, item_id, values):
        raise _not_found()
    await session.commit()
    return await compute.roadmap_for(session, user_id)


@router.delete("/roadmap/items/{item_id}", response_model=Roadmap)
async def delete_step(item_id: UUID, user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    if not await roadmap_items.delete_item(session, user_id, item_id):
        raise _not_found()
    await session.commit()
    return await compute.roadmap_for(session, user_id)


@router.get("/roadmap.ics")
async def roadmap_ics(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    return Response(content=ics.roadmap_to_ics(await compute.roadmap_for(session, user_id)), media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="applyra-route.ics"'})


@router.get("/favorites", response_model=list[str])
async def get_favorites(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    return await profiles.favorite_ids(session, user_id)


async def _toggle_favorite(session: AsyncSession, user_id: UUID, university_id: str, on: bool) -> ComputeResponse:
    unis = {u.id: u for u in await catalog.universities(session)}
    if university_id not in unis:
        raise HTTPException(status_code=404, detail={"code": "UNIVERSITY_NOT_FOUND", "message": "Вуз не найден"})
    prev = await compute.require_profile(session, user_id)
    await profiles.set_favorite(session, user_id, university_id, on)
    cause = f"{'Добавлен в план' if on else 'Убран из плана'}: {unis[university_id].name}"
    return await compute.recompute(session, user_id, prev, cause=cause)


@router.put("/favorites/{university_id}", response_model=ComputeResponse)
async def add_favorite(university_id: str, user_id: UUID = Depends(get_user_id),
                       session: AsyncSession = Depends(get_session)):
    return await _toggle_favorite(session, user_id, university_id, True)


@router.delete("/favorites/{university_id}", response_model=ComputeResponse)
async def remove_favorite(university_id: str, user_id: UUID = Depends(get_user_id),
                          session: AsyncSession = Depends(get_session)):
    return await _toggle_favorite(session, user_id, university_id, False)
