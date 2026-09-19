from typing import Literal

from pydantic import BaseModel

EssayLevel = Literal["bachelor", "master", "phd", "mba", "other"]
EssayKind = Literal["common_app", "personal_statement", "statement_of_purpose", "other"]


class EssaySummary(BaseModel):
    id: str
    school: str | None
    university_id: str | None          # catalog id when the school is in our catalog
    level: EssayLevel
    kind: EssayKind
    prompt: str | None = None          # essay question, when the source states one
    program: str | None
    majors: list[str]                  # catalog major ids
    topics: list[str]
    author: str | None
    license: Literal["CC_BY_NC_SA_4_0", "UNKNOWN"]
    source_url: str
    original_url: str | None
    word_count: int
    excerpt: str


class Essay(EssaySummary):
    body: str
    references: list[str] = []


class RecommendedEssay(BaseModel):
    essay: EssaySummary
    reasons: list[str]
