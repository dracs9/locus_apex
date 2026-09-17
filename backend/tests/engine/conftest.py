from datetime import date, datetime
from uuid import uuid4

import pytest

from app.schemas import Achievement, Priorities, Profile, University

TODAY = date(2026, 9, 17)


def make_uni(id_="uni", **kw) -> University:
    data = {
        "id": id_,
        "name": id_.upper(),
        "country": "US",
        "city": "Town",
        "website": "https://example.edu",
        "majors": ["cs", "economics"],
        "acceptance_rate": {"value": 0.25, "is_demo": True},
        "sat": {"value": {"p25": 1400, "p75": 1520}, "is_demo": True},
        "gpa_avg": {"value": 3.6, "is_demo": True},
        "ielts_min": {"value": 6.5, "is_demo": True},
        "cost_per_year_usd": {"value": 40000, "is_demo": True},
        "intl_aid": {"value": "none", "is_demo": True},
        "deadlines": [{"value": {"type": "RD", "date": "2027-01-15"}, "is_demo": True}],
        "extra_requirements": [],
        "documents": ["transcript", "essay"],
        "world_rank": 100,
    }
    data.update(kw)
    return University.model_validate(data)


def ach(type_, score=None, status="done", on=date(2026, 6, 1), level=None, title=None) -> Achievement:
    return Achievement(id=uuid4(), type=type_, score=score, status=status, date=on, level=level, title=title)


def make_profile(**kw) -> Profile:
    data = {
        "grade": 11,
        "gpa5": 4.8,  # ≈3.8 on the 4.0 scale
        "majors": ["cs"],
        "countries": ["US", "UK"],
        "budget_per_year_usd": 50000,
        "needs_aid": False,
        "intake_year": 2027,
        "priorities": Priorities(),
        "achievements": [ach("SAT", 1450), ach("IELTS", 7.0)],
        "created_at": datetime(2026, 5, 1),
    }
    data.update(kw)
    return Profile.model_validate(data)


@pytest.fixture
def today() -> date:
    return TODAY
