from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReasonKind = Literal["plus", "risk", "blocker"]
Tier = Literal["dream", "target", "safety"]
Chance = Literal["low", "medium", "high"]


class Reason(BaseModel):
    kind: ReasonKind
    code: str
    text: str
    profile_field: str
    gap: float | None = None


class Recommendation(BaseModel):
    university_id: str
    tier: Tier
    chance: Chance
    score: float
    reasons: list[Reason]


class Excluded(BaseModel):
    university_id: str
    reasons: list[Reason]


class RecommendationResult(BaseModel):
    recs: list[Recommendation]
    excluded: list[Excluded]
    suggestions: list[str]
    computed_at: datetime
