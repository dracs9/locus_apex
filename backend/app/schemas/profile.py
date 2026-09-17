import datetime as dt
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AchievementType = Literal["SAT", "IELTS", "TOEFL", "OLYMPIAD", "PROJECT", "VOLUNTEER", "COMPETITION", "OTHER"]
AchievementLevel = Literal["school", "city", "national", "international"]
AchievementStatus = Literal["done", "planned"]


class Achievement(BaseModel):
    id: UUID
    type: AchievementType
    score: float | None = None
    title: str | None = None
    level: AchievementLevel | None = None
    date: dt.date
    status: AchievementStatus


class AchievementIn(BaseModel):
    type: AchievementType
    score: float | None = None
    title: str | None = None
    level: AchievementLevel | None = None
    date: dt.date
    status: AchievementStatus = "done"


class AchievementPatch(BaseModel):
    type: AchievementType | None = None
    score: float | None = None
    title: str | None = None
    level: AchievementLevel | None = None
    date: dt.date | None = None
    status: AchievementStatus | None = None


class Priorities(BaseModel):
    cost: float = Field(0.5, ge=0, le=1)
    prestige: float = Field(0.5, ge=0, le=1)
    location: float = Field(0.5, ge=0, le=1)
    aid: float = Field(0.5, ge=0, le=1)


class Profile(BaseModel):
    grade: Literal[10, 11, 12]
    gpa5: float = Field(ge=2.0, le=5.0)
    majors: list[str] = Field(min_length=1, max_length=3)
    countries: list[str] = Field(min_length=1)
    budget_per_year_usd: int = Field(ge=0)
    needs_aid: bool
    intake_year: int
    priorities: Priorities
    achievements: list[Achievement] = []
    created_at: datetime


class ProfileIn(BaseModel):
    """Profile body for PUT /me/profile. Achievements are managed separately, but
    onboarding may send initial ones (without ids)."""

    grade: Literal[10, 11, 12]
    gpa5: float = Field(ge=2.0, le=5.0)
    majors: list[str] = Field(min_length=1, max_length=3)
    countries: list[str] = Field(min_length=1)
    budget_per_year_usd: int = Field(ge=0)
    needs_aid: bool
    intake_year: int
    priorities: Priorities
    initial_achievements: list[AchievementIn] = []
