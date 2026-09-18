"""Change flow (§7): prev snapshot -> (change already saved) -> recommend + roadmap -> diff -> save snapshot."""
import hashlib
import json
from datetime import date
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.diff import describe_changes, diff
from app.engine.recommend import recommend
from app.engine.roadmap import build_roadmap
from app.schemas import ComputeResponse, Profile, RecommendationResult, Roadmap, Snapshot

from . import catalog, profiles, snapshots


def today() -> date:
    return date.today()


def profile_hash(profile: Profile, favorite_ids: list[str]) -> str:
    # attachments never affect scoring, and signed photo URLs change on every load
    data = profile.model_dump(mode="json", exclude={"created_at": True, "achievements": {"__all__": {"attachments"}}})
    payload = json.dumps({"p": data, "f": favorite_ids}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def require_profile(session: AsyncSession, user_id: UUID) -> Profile:
    profile = await profiles.load_profile(session, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail={"code": "PROFILE_NOT_FOUND", "message": "Профиль ещё не создан"})
    return profile


async def roadmap_for(session: AsyncSession, user_id: UUID, profile: Profile, result: RecommendationResult) -> Roadmap:
    unis = await catalog.universities(session)
    return build_roadmap(profile, await profiles.favorite_ids(session, user_id), result.recs, unis,
                         await profiles.progress(session, user_id), today())


async def current_result(session: AsyncSession, user_id: UUID, profile: Profile) -> RecommendationResult:
    """Latest snapshot result if it matches the profile, otherwise a fresh computation."""
    last = await snapshots.latest(session, user_id)
    favs = await profiles.favorite_ids(session, user_id)
    if last and last[0].profile_hash == profile_hash(profile, favs) and last[0].at.date() == today():
        return last[0].result
    return recommend(profile, await catalog.universities(session), today(), await catalog.major_names(session))


async def recompute(session: AsyncSession, user_id: UUID, prev_profile: Profile | None,
                    cause: str | None = None, profile: Profile | None = None) -> ComputeResponse:
    """Call after the change is written (not yet committed). Commits the transaction.

    Pass `profile` when the caller already holds the post-change profile — re-reading it here
    costs two more round trips, which is a lot on a remote database.
    """
    profile = profile or await require_profile(session, user_id)
    unis = await catalog.universities(session)
    names = await catalog.major_names(session)
    favs = await profiles.favorite_ids(session, user_id)

    prev = await snapshots.latest(session, user_id)
    result = recommend(profile, unis, today(), names)
    result.computed_at = profiles.now()
    roadmap = build_roadmap(profile, favs, result.recs, unis, await profiles.progress(session, user_id), today())

    snap = Snapshot(id=uuid4(), at=profiles.now(), result=result, roadmap_step_ids=[s.id for s in roadmap.steps],
                    profile_hash=profile_hash(profile, favs),
                    cause=cause or describe_changes(prev_profile, profile, names))
    d = diff(prev[0] if prev else None, snap)
    await snapshots.save(session, user_id, snap, d)
    await session.commit()
    return ComputeResponse(result=result, roadmap=roadmap, diff=d)
