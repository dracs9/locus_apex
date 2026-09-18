from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.engine.history import chance_history
from app.engine.roadmap import target_ids
from app.schemas import ChancePoint
from app.services import catalog, compute, profiles

router = APIRouter(prefix="/me", tags=["history"])


@router.get("/chance-history", response_model=list[ChancePoint])
async def get_chance_history(ids: str | None = Query(default=None, description="comma-separated university ids"),
                             user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    unis = await catalog.universities(session)
    if ids:
        university_ids = [i for i in ids.split(",") if i][:5]
    else:
        university_ids = (await profiles.favorite_ids(session, user_id))[:3]
        if not university_ids:
            result = await compute.current_result(session, user_id, profile)
            university_ids = target_ids([], result.recs, unis)
    return chance_history(profile, university_ids, unis, await catalog.major_names(session))
