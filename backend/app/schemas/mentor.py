from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .roadmap import Roadmap

ActionType = Literal["add_suggestion", "add_step", "update_step", "delete_step"]
ActionStatus = Literal["pending", "applied", "dismissed", "failed"]


class MentorAction(BaseModel):
    """A plan change the mentor proposed. Nothing changes until the student applies it."""
    type: ActionType
    summary: str
    args: dict[str, Any]
    status: ActionStatus = "pending"


class MentorMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    text: str
    actions: list[MentorAction] = []
    generated: bool = False
    created_at: datetime


class MentorIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class MentorReply(BaseModel):
    messages: list[MentorMessage]


class ActionIn(BaseModel):
    apply: bool


class ActionResult(BaseModel):
    message: MentorMessage
    roadmap: Roadmap | None = None
