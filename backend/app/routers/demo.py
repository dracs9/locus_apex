import json
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas import AchievementIn, ComputeResponse, ProfileIn, Suggestion
from app.services import attachments, compute, profiles, roadmap_items, storage

router = APIRouter(prefix="/me", tags=["demo"])

DEMO_PATH = Path(__file__).parent.parent / "data" / "demo_profile.json"
DEMO_PLAN_PER_KIND = 2


def demo_plan(suggestions: list[Suggestion]) -> list[Suggestion]:
    """The first suggestions of each kind (they are already sorted by date)."""
    picked: list[Suggestion] = []
    for kind in ("exam", "activity", "document", "application"):
        picked += [s for s in suggestions if s.kind == kind][:DEMO_PLAN_PER_KIND]
    return picked


@router.post("/demo", response_model=ComputeResponse)
async def load_demo(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    data = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    body = ProfileIn.model_validate({**data, "initial_achievements": [AchievementIn.model_validate(a) for a in data["achievements"]]})
    paths = await attachments.photo_paths(session, user_id)
    await profiles.wipe_user(session, user_id)
    # the demo profile "was created" half a year ago so the chance history has a starting point
    await profiles.save_profile(session, user_id, body, profiles.now() - timedelta(days=180))
    res = await compute.recompute(session, user_id, None, cause="Загружен демо-профиль")
    # The plan is the student's own, but a demo should show one: take the nearest suggestions of each kind.
    profile = await compute.require_profile(session, user_id)
    for s in demo_plan(await compute.suggestions_for(session, user_id, profile, res.result)):
        await roadmap_items.add_item(session, user_id, kind=s.kind, title=s.title, due_date=s.suggested_due,
                                     source_key=s.id, university_ids=s.university_ids, source_url=s.source_url,
                                     is_demo=s.is_demo)
    await session.commit()
    res.roadmap = await compute.roadmap_for(session, user_id)
    await storage.remove_quietly(paths)
    return res


@router.post("/reset")
async def reset(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    paths = await attachments.photo_paths(session, user_id)
    await profiles.wipe_user(session, user_id)
    await session.commit()
    await storage.remove_quietly(paths)
    return {"ok": True}
