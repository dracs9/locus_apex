import datetime as dt
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .recommendation import Chance, RecommendationResult, Tier

StepKind = Literal["exam", "document", "academic", "activity", "application"]


class RoadmapStep(BaseModel):
    id: str
    kind: StepKind
    title: str
    due_date: dt.date
    depends_on: list[str]
    university_ids: list[str]
    source_url: str | None = None
    is_demo: bool
    done: bool
    priority: int


class Conflict(BaseModel):
    step_id: str
    message: str


class Roadmap(BaseModel):
    steps: list[RoadmapStep]
    conflicts: list[Conflict]
    next_step_id: str | None
    progress: float


class TierChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    from_: Tier = Field(alias="from")
    to: Tier


class ChanceChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    from_: Chance = Field(alias="from")
    to: Chance


class GapClosed(BaseModel):
    id: str
    code: str


class Diff(BaseModel):
    added: list[str]
    removed: list[str]
    tier_changed: list[TierChange]
    chance_changed: list[ChanceChange]
    gaps_closed: list[GapClosed]
    roadmap_added: list[str]
    roadmap_removed: list[str]
    cause: str


class Snapshot(BaseModel):
    id: UUID
    at: datetime
    result: RecommendationResult
    roadmap_step_ids: list[str]
    profile_hash: str
    cause: str


class ComputeResponse(BaseModel):
    result: RecommendationResult
    roadmap: Roadmap
    diff: Diff | None


class ChancePoint(BaseModel):
    date: dt.date
    chance_by_uni: dict[str, Chance | None]
    achievement_id: str | None
