import json
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import AchievementIn, ComputeResponse, ProfileIn
from app.services import compute, profiles

router = APIRouter(prefix="/me", tags=["demo"])

DEMO_PATH = Path(__file__).parent.parent / "data" / "demo_profile.json"


@router.post("/demo", response_model=ComputeResponse)
async def load_demo(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    data = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    body = ProfileIn.model_validate({**data, "initial_achievements": [AchievementIn.model_validate(a) for a in data["achievements"]]})
    await profiles.wipe_user(session, user_id)
    # the demo profile "was created" half a year ago so the chance history has a starting point
    await profiles.save_profile(session, user_id, body, profiles.now() - timedelta(days=180))
    return await compute.recompute(session, user_id, None, cause="Загружен демо-профиль")


@router.post("/reset")
async def reset(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    await profiles.wipe_user(session, user_id)
    await session.commit()
    return {"ok": True}
