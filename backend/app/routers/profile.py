from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import ComputeResponse, Profile, ProfileIn
from app.services import attachments, compute, profiles

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("/profile", response_model=Profile)
async def get_profile(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    by_achievement = await attachments.list_for(session, user_id)
    for a in profile.achievements:
        a.attachments = by_achievement.get(a.id, [])
    return profile


@router.put("/profile", response_model=ComputeResponse)
async def put_profile(body: ProfileIn, user_id: UUID = Depends(get_user_id),
                      session: AsyncSession = Depends(get_session)):
    prev = await profiles.load_profile(session, user_id)
    await profiles.save_profile(session, user_id, body, prev.created_at if prev else None)
    return await compute.recompute(session, user_id, prev)
