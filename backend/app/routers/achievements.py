from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import (MAX_PHOTO_BYTES, AchievementCreated, AchievementIn, AchievementPatch, Attachment,
                         ComputeResponse, LinkIn)
from app.services import attachments, compute, profiles, storage

router = APIRouter(prefix="/me/achievements", tags=["achievements"])

NOT_FOUND = HTTPException(status_code=404, detail={"code": "ACHIEVEMENT_NOT_FOUND", "message": "Достижение не найдено"})


@router.post("", response_model=AchievementCreated)
async def create_achievement(body: AchievementIn, user_id: UUID = Depends(get_user_id),
                             session: AsyncSession = Depends(get_session)):
    prev = await compute.require_profile(session, user_id)
    achievement_id = await profiles.add_achievement(session, user_id, body)
    res = await compute.recompute(session, user_id, prev)
    return AchievementCreated(**res.model_dump(), achievement_id=achievement_id)


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
    paths = await attachments.photo_paths(session, user_id, achievement_id)
    if not await profiles.delete_achievement(session, user_id, achievement_id):
        raise NOT_FOUND
    res = await compute.recompute(session, user_id, prev)
    await storage.remove_quietly(paths)
    return res


# --- attachments: photos and links (no recomputation, they don't affect scoring) ---

@router.post("/{achievement_id}/attachments/link", response_model=Attachment, status_code=201)
async def add_link(achievement_id: UUID, body: LinkIn, user_id: UUID = Depends(get_user_id),
                   session: AsyncSession = Depends(get_session)):
    return await attachments.add_link(session, user_id, achievement_id, body)


@router.post("/{achievement_id}/attachments/photo", response_model=Attachment, status_code=201)
async def add_photo(achievement_id: UUID, file: UploadFile = File(...), title: str | None = Form(default=None),
                    user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    data = await file.read(MAX_PHOTO_BYTES + 1)  # never read more than the limit
    return await attachments.add_photo(session, user_id, achievement_id, data, title)


@router.delete("/{achievement_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(achievement_id: UUID, attachment_id: UUID, user_id: UUID = Depends(get_user_id),
                            session: AsyncSession = Depends(get_session)):
    await attachments.delete_one(session, user_id, achievement_id, attachment_id)
    return Response(status_code=204)
