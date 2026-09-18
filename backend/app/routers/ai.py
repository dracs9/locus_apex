"""LLM texts with template fallbacks (§9). The LLM only rephrases engine output."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.llm import cache, fallbacks, prompts
from app.llm.client import generate_json
from app.schemas.ai import ExplainIn, ExplainOut, PassportOut, RoadmapTextIn, RoadmapTextOut, StepText
from app.services import catalog, compute

router = APIRouter(prefix="/ai", tags=["ai"])


async def _llm(session: AsyncSession, kind: str, system: str, payload: dict) -> dict | None:
    key = cache.cache_key(kind, payload)
    hit = await cache.get(session, key)
    if hit is not None:
        return hit
    # The SELECT above opened a transaction; release it before waiting on the LLM.
    # Session-mode pooling pins a server backend per connection, so an idle-in-transaction
    # holder for the whole 8 s timeout is what starves the pool.
    await session.rollback()
    out = await generate_json(system, payload)
    if isinstance(out, dict):
        await cache.put(session, key, out)
        return out
    return None


@router.post("/passport", response_model=PassportOut)
async def passport(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    result = await compute.current_result(session, user_id, profile)
    template = fallbacks.passport(profile, result, await catalog.major_names(session))
    draft = template.model_dump(exclude={"generated"})
    out = await _llm(session, "passport", prompts.PASSPORT,
                     {"fields": profile.model_dump(mode="json", exclude={"created_at"}), "draft": draft})
    if out is None:
        return template
    try:
        generated = PassportOut.model_validate({**out, "generated": True})
    except ValidationError:
        return template
    allowed = {i.profile_field for i in [template.goal, template.risk, *template.strengths, *template.constraints]}
    items = [generated.goal, generated.risk, *generated.strengths, *generated.constraints]
    if any(i.profile_field not in allowed for i in items) or any("%" in i.text for i in items):
        return template
    return generated


@router.post("/explain", response_model=ExplainOut)
async def explain(body: ExplainIn, user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    uni = next((u for u in await catalog.universities(session) if u.id == body.university_id), None)
    if uni is None:
        raise HTTPException(status_code=404, detail={"code": "UNIVERSITY_NOT_FOUND", "message": "Вуз не найден"})
    result = await compute.current_result(session, user_id, profile)
    rec = next((r for r in result.recs if r.university_id == uni.id), None)
    excluded = next((e for e in result.excluded if e.university_id == uni.id), None)
    reasons = rec.reasons if rec else (excluded.reasons if excluded else [])
    tier = rec.tier if rec else None
    template = ExplainOut(university_id=uni.id, summary=fallbacks.explain(uni, [(r.kind, r.text) for r in reasons], tier))
    if not reasons:
        return template
    out = await _llm(session, "explain", prompts.EXPLAIN,
                     {"university": uni.name, "tier": tier or "excluded", "reasons": [r.text for r in reasons]})
    try:
        summary = str(out["summary"]).strip() if out else ""
    except (KeyError, TypeError):
        summary = ""
    if not summary or "%" in summary or len(summary) > 500:
        return template
    return ExplainOut(university_id=uni.id, summary=summary, generated=True)


@router.post("/roadmap-text", response_model=RoadmapTextOut)
async def roadmap_text(body: RoadmapTextIn, user_id: UUID = Depends(get_user_id),
                       session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    result = await compute.current_result(session, user_id, profile)
    roadmap = await compute.roadmap_for(session, user_id, profile, result)
    steps = [s for s in roadmap.steps if s.id in set(body.step_ids)]
    template = RoadmapTextOut(items=[StepText(id=s.id, description=fallbacks.step_description(s)) for s in steps])
    if not steps:
        return template
    out = await _llm(session, "roadmap-text", prompts.ROADMAP_TEXT,
                     {"steps": [{"id": s.id, "title": s.title, "kind": s.kind, "due_date": s.due_date.isoformat()}
                                for s in steps]})
    try:
        generated = RoadmapTextOut.model_validate({**(out or {}), "generated": True})
    except ValidationError:
        return template
    if [i.id for i in generated.items] != [s.id for s in steps] or any("%" in i.description for i in generated.items):
        return template
    return generated
