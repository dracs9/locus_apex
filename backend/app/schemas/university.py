import datetime as dt
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

AidType = Literal["full_need", "partial", "merit_only", "none"]
DeadlineType = Literal["ED", "EA", "REA", "RD", "UCAS", "OTHER"]


class Sourced(BaseModel, Generic[T]):
    value: T | None
    source_url: str | None = None
    checked_at: dt.date | None = None
    evidence: str | None = None
    is_demo: bool = True


class SatRange(BaseModel):
    p25: int
    p50: int | None = None
    p75: int


class Deadline(BaseModel):
    type: DeadlineType
    date: dt.date


class University(BaseModel):
    id: str
    name: str
    country: str
    city: str
    website: str
    majors: list[str]
    acceptance_rate: Sourced[float]
    sat: Sourced[SatRange]
    gpa_avg: Sourced[float]
    ielts_min: Sourced[float]
    cost_per_year_usd: Sourced[int]
    intl_aid: Sourced[AidType]
    deadlines: list[Sourced[Deadline]]
    extra_requirements: list[str] = []
    documents: list[str] = []
    world_rank: int


class Major(BaseModel):
    id: str
    name_ru: str
    name_en: str
    cip_codes: list[str] = []
