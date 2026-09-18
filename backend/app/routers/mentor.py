"""AI mentor chat (§9 extension). The mentor proposes plan changes; the student applies or dismisses each."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_user_id
from app.schemas.mentor import ActionIn, ActionResult, MentorIn, MentorMessage, MentorReply
from app.services import compute, mentor_store, plan
from app.services.mentor import Mentor, apply_action

router = APIRouter(prefix="/ai/mentor", tags=["mentor"])


@router.get("", response_model=list[MentorMessage])
async def get_messages(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    await compute.require_profile(session, user_id)
    return await mentor_store.list_messages(session, user_id)


@router.post("", response_model=MentorReply)
async def send(body: MentorIn, user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    profile = await compute.require_profile(session, user_id)
    past = await mentor_store.list_messages(session, user_id, limit=12)
    mentor = Mentor(session, user_id, profile, compute.today())
    await mentor.load()
    # Release the read transaction before waiting on the model (see ai._llm).
    await session.rollback()
    text, generated = await mentor.reply(past, body.text.strip())
    user_msg = await mentor_store.add_message(session, user_id, "user", body.text.strip())
    reply = await mentor_store.add_message(session, user_id, "assistant", text, mentor.actions, generated)
    await session.commit()
    return MentorReply(messages=[user_msg, reply])


@router.post("/{message_id}/actions/{index}", response_model=ActionResult)
async def act(message_id: UUID, index: int, body: ActionIn, user_id: UUID = Depends(get_user_id),
              session: AsyncSession = Depends(get_session)):
    msg = await mentor_store.get_message(session, user_id, message_id)
    if msg is None or not 0 <= index < len(msg.actions):
        raise HTTPException(status_code=404, detail={"code": "ACTION_NOT_FOUND", "message": "Предложение не найдено"})
    action = msg.actions[index]
    if action.status != "pending":
        raise HTTPException(status_code=409, detail={"code": "ACTION_DONE", "message": "Предложение уже обработано"})
    roadmap = None
    if body.apply:
        profile = await compute.require_profile(session, user_id)
        try:
            await apply_action(session, user_id, profile, action)
        except (plan.PlanError, KeyError, ValueError) as e:
            await session.rollback()
            action.status = "failed"
            await mentor_store.save_actions(session, user_id, msg)
            await session.commit()
            message = e.message if isinstance(e, plan.PlanError) else "Предложение устарело"
            raise HTTPException(status_code=409, detail={"code": "ACTION_FAILED", "message": message}) from e
        action.status = "applied"
    else:
        action.status = "dismissed"
    await mentor_store.save_actions(session, user_id, msg)
    await session.commit()
    if body.apply:
        roadmap = await compute.roadmap_for(session, user_id)
    return ActionResult(message=msg, roadmap=roadmap)


@router.delete("", status_code=204)
async def clear(user_id: UUID = Depends(get_user_id), session: AsyncSession = Depends(get_session)):
    await mentor_store.clear(session, user_id)
    await session.commit()
