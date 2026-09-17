from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import AchievementIn, AchievementPatch, ComputeResponse
from app.services import compute, profiles

router = APIRouter(prefix="/me/achievements", tags=["achievements"])

NOT_FOUND = HTTPException(status_code=404, detail={"code": "ACHIEVEMENT_NOT_FOUND", "message": "Достижение не найдено"})


@router.post("", response_model=ComputeResponse)
async def create_achievement(body: AchievementIn, user_id: UUID = Depends(get_user_id),
                             session: AsyncSession = Depends(get_session)):
    prev = await compute.require_profile(session, user_id)
    await profiles.add_achievement(session, user_id, body)
    return await compute.recompute(session, user_id, prev)


@router.patch("/{achievement_id}", response_model=ComputeResponse)
async def patch_achievement(achievement_id: UUID, body: AchievementPatch, user_id: UUID = Depends(get_user_id),
                            session: AsyncSession = Depends(get_session)):
    prev = await compute.require_profile(session, user_id)
    values = body.model_dump(exclude_unset=True)
    if values and not await profiles.update_achievement(session, user_id, achievement_id, values):
        raise NOT_FOUND
    return await compute.recompute(session, user_id, prev)


@router.delete("/{achievement_id}", response_model=ComputeResponse)
async def delete_achievement(achievement_id: UUID, user_id: UUID = Depends(get_user_id),
                             session: AsyncSession = Depends(get_session)):
    prev = await compute.require_profile(session, user_id)
    if not await profiles.delete_achievement(session, user_id, achievement_id):
        raise NOT_FOUND
    return await compute.recompute(session, user_id, prev)
