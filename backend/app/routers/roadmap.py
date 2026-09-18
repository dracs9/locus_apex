from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import ComputeResponse, Roadmap, StepIn, StepPatch, Suggestion
from app.services import catalog, compute, ics, plan, profiles

router = APIRouter(prefix="/me", tags=["roadmap"])


def _http(e: plan.PlanError) -> HTTPException:
    return HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})


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
    try:
        if body.suggestion_id:
            await plan.add_from_suggestion(session, user_id, profile, body.suggestion_id, title=body.title,
                                           kind=body.kind, due_date=body.due_date, note=body.note)
        else:
            await plan.add_custom(session, user_id, title=body.title, kind=body.kind, due_date=body.due_date,
                                  note=body.note)
    except plan.PlanError as e:
        raise _http(e) from e
    await session.commit()
    return await compute.roadmap_for(session, user_id)


@router.patch("/roadmap/items/{item_id}", response_model=Roadmap)
async def patch_step(item_id: UUID, body: StepPatch, user_id: UUID = Depends(get_user_id),
                     session: AsyncSession = Depends(get_session)):
    try:
        await plan.patch(session, user_id, item_id, body.model_dump(exclude_unset=True))
    except plan.PlanError as e:
        raise _http(e) from e
    await session.commit()
    return await compute.roadmap_for(session, user_id)


@router.delete("/roadmap/items/{item_id}", response_model=Roadmap)
async def delete_step(item_id: UUID, user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    try:
        await plan.delete(session, user_id, item_id)
    except plan.PlanError as e:
        raise _http(e) from e
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
