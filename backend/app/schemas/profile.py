import datetime as dt
from datetime import datetime
from typing import Annotated, Literal
import json
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator

AchievementType = Literal["SAT", "IELTS", "TOEFL", "OLYMPIAD", "PROJECT", "VOLUNTEER", "COMPETITION", "OTHER"]
AchievementLevel = Literal["school", "city", "national", "international"]
AchievementStatus = Literal["done", "planned"]
AttachmentKind = Literal["photo", "link"]
MAX_ATTACHMENTS = 5
MAX_PHOTO_BYTES = 5 * 1024 * 1024


class Attachment(BaseModel):
    id: UUID
    kind: AttachmentKind
    url: str | None = None  # link target, or a short-lived signed URL for photos
    title: str | None = None
    content_type: str | None = None
    created_at: datetime


class LinkIn(BaseModel):
    url: HttpUrl = Field(max_length=2048)
    title: str | None = Field(default=None, max_length=120)


class Achievement(BaseModel):
    id: UUID
    type: AchievementType
    score: float | None = None
    title: str | None = None
    level: AchievementLevel | None = None
    date: dt.date
    status: AchievementStatus
    attachments: list[Attachment] = []


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


class AcademicRecord(BaseModel):
    scale: Literal["5", "4", "100", "ib8"]
    value: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_range(self):
        maximum = {"5": 5, "4": 4, "100": 100, "ib8": 8}[self.scale]
        if self.value > maximum:
            raise ValueError("Средний балл превышает выбранную шкалу")
        return self


class HollandAssessment(BaseModel):
    version: Literal["applyra-riasec-v1"] = "applyra-riasec-v1"
    answers: dict[str, Annotated[int, Field(strict=True, ge=0, le=4)]]

    @model_validator(mode="after")
    def complete_questionnaire(self):
        data = json.loads((Path(__file__).parents[1] / "data/holland.json").read_text())
        if set(self.answers) != {q["id"] for q in data["questions"]}:
            raise ValueError("Ответьте на все 30 вопросов RIASEC")
        return self


class Profile(BaseModel):
    grade: Literal[9, 10, 11, 12]
    gpa5: float | None = Field(default=None, ge=0, le=5.0)
    academic_record: AcademicRecord | None = None
    holland: HollandAssessment | None = None
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

    grade: Literal[9, 10, 11, 12]
    gpa5: float | None = Field(default=None, ge=0, le=5.0)
    academic_record: AcademicRecord | None = None
    holland: HollandAssessment | None = None
    majors: list[str] = Field(min_length=1, max_length=3)
    countries: list[str] = Field(min_length=1)
    budget_per_year_usd: int = Field(ge=0)
    needs_aid: bool
    intake_year: int
    priorities: Priorities
    initial_achievements: list[AchievementIn] = []
