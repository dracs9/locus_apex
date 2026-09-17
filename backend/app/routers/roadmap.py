from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import ComputeResponse, Roadmap
from app.services import catalog, compute, ics, profiles

router = APIRouter(prefix="/me", tags=["roadmap"])


class StepPatch(BaseModel):
    done: bool


async def _roadmap(session: AsyncSession, user_id: UUID) -> Roadmap:
    profile = await compute.require_profile(session, user_id)
    result = await compute.current_result(session, user_id, profile)
    return await compute.roadmap_for(session, user_id, profile, result)


@router.get("/roadmap", response_model=Roadmap)
async def get_roadmap(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    return await _roadmap(session, user_id)


@router.patch("/roadmap/steps/{step_id}", response_model=Roadmap)
async def patch_step(step_id: str, body: StepPatch, user_id: UUID = Depends(get_user_id),
                     session: AsyncSession = Depends(get_session)):
    await profiles.set_progress(session, user_id, step_id, body.done)
    await session.commit()
    return await _roadmap(session, user_id)


@router.get("/roadmap.ics")
async def roadmap_ics(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    return Response(content=ics.roadmap_to_ics(await _roadmap(session, user_id)), media_type="text/calendar; charset=utf-8",
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
