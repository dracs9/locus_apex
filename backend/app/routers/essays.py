from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import Essay, EssaySummary, RecommendedEssay
from app.services import catalog, compute, essays, profiles

router = APIRouter(tags=["essays"])


@router.get("/essays", response_model=list[EssaySummary])
async def list_essays(session: AsyncSession = Depends(get_session)):
    return await essays.summaries(session)


@router.get("/essays/{essay_id}", response_model=Essay)
async def get_essay(essay_id: str, session: AsyncSession = Depends(get_session)):
    essay = await essays.get(session, essay_id)
    if essay is None:
        raise HTTPException(status_code=404, detail={"code": "ESSAY_NOT_FOUND", "message": "Эссе не найдено"})
    return essay


@router.get("/me/essays/recommended", response_model=list[RecommendedEssay])
async def recommended_essays(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await profiles.load_profile(session, user_id)
    favorite_ids = await profiles.favorite_ids(session, user_id) if profile else []
    rec_ids = [r.university_id for r in (await compute.current_result(session, user_id, profile)).recs] if profile else []
    names = {u.id: u.name for u in await catalog.universities(session)}
    return essays.recommend_essays(await essays.summaries(session), profile, favorite_ids, rec_ids, names,
                                   await catalog.major_names(session))
