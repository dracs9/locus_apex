import datetime as dt
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .recommendation import Chance, RecommendationResult, Tier

StepKind = Literal["exam", "document", "academic", "activity", "application"]
SuggestionCategory = Literal["exam", "document", "academic", "activity", "application"]


class RoadmapStep(BaseModel):
    """A step of the student's own plan (a stored roadmap item)."""
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
    source_key: str | None = None      # suggestion it was added from; None for a custom step
    note: str | None = None


class SuggestionWhy(BaseModel):
    text: str
    profile_field: str


class Suggestion(BaseModel):
    """What the engine recommends adding to the plan. Deterministic; never saved until the student adds it."""
    id: str                            # deterministic key: 'exam:SAT', 'doc:essay', 'apply:mit:RD', 'act:olympiad'
    kind: StepKind
    title: str
    why: SuggestionWhy
    description: str                   # template text; /ai/roadmap-text may rephrase it
    suggested_due: dt.date
    university_ids: list[str]
    source_url: str | None = None
    is_demo: bool
    priority: int


class StepIn(BaseModel):
    """Add a step: from a suggestion (fields optional overrides) or a custom one (title, kind, due_date required)."""
    suggestion_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kind: StepKind | None = None
    due_date: dt.date | None = None
    note: str | None = Field(default=None, max_length=1000)


class StepPatch(BaseModel):
    done: bool | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    kind: StepKind | None = None
    due_date: dt.date | None = None
    note: str | None = Field(default=None, max_length=1000)


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


class AchievementCreated(ComputeResponse):
    achievement_id: UUID


class ChancePoint(BaseModel):
    date: dt.date
    chance_by_uni: dict[str, Chance | None]
    achievement_id: str | None
