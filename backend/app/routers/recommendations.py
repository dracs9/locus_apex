from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.engine.normalize import with_priorities
from app.engine.recommend import recommend
from app.schemas import Diff, Priorities, Profile, RecommendationResult
from app.services import catalog, compute, snapshots

router = APIRouter(tags=["recommendations"])


class PreviewIn(BaseModel):
    profile: Profile
    priorities_override: Priorities | None = None


class LatestChanges(BaseModel):
    diff: Diff | None
    cause: str | None
    at: str | None


@router.get("/me/recommendations", response_model=RecommendationResult)
async def get_recommendations(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    return await compute.current_result(session, user_id, profile)


@router.post("/preview", response_model=RecommendationResult)
async def preview(body: PreviewIn, session: AsyncSession = Depends(get_session)):
    """Stateless what-if: never writes anything."""
    profile = with_priorities(body.profile, body.priorities_override)
    return recommend(profile, await catalog.universities(session), compute.today(), await catalog.major_names(session))


@router.get("/me/changes/latest", response_model=LatestChanges)
async def latest_changes(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    last = await snapshots.latest(session, user_id)
    if last is None:
        return LatestChanges(diff=None, cause=None, at=None)
    snap, diff = last
    return LatestChanges(diff=diff, cause=snap.cause, at=snap.at.isoformat())
