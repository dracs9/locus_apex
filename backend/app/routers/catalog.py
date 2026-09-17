from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.schemas import Major, University
from app.services import catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/universities", response_model=list[University])
async def list_universities(session: AsyncSession = Depends(get_session)):
    return await catalog.universities(session)


@router.get("/universities/{university_id}", response_model=University)
async def get_university(university_id: str, session: AsyncSession = Depends(get_session)):
    uni = next((u for u in await catalog.universities(session) if u.id == university_id), None)
    if uni is None:
        raise HTTPException(status_code=404, detail={"code": "UNIVERSITY_NOT_FOUND", "message": "Вуз не найден"})
    return uni


@router.get("/majors", response_model=list[Major])
async def list_majors(session: AsyncSession = Depends(get_session)):
    return await catalog.majors(session)
