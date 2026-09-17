from pydantic import BaseModel, Field


class PassportItem(BaseModel):
    text: str = Field(max_length=240)
    profile_field: str


class PassportOut(BaseModel):
    goal: PassportItem
    strengths: list[PassportItem] = Field(min_length=1, max_length=3)
    constraints: list[PassportItem] = Field(min_length=1, max_length=2)
    risk: PassportItem
    generated: bool = False


class ExplainIn(BaseModel):
    university_id: str


class ExplainOut(BaseModel):
    university_id: str
    summary: str = Field(max_length=500)
    generated: bool = False


class RoadmapTextIn(BaseModel):
    step_ids: list[str] = Field(max_length=40)


class StepText(BaseModel):
    id: str
    description: str = Field(max_length=400)


class RoadmapTextOut(BaseModel):
    items: list[StepText]
    generated: bool = False
