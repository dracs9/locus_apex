import json
from pathlib import Path

from app.schemas import EssaySummary, Profile
from app.services import essays

from .test_api import PROFILE

SEED = json.loads((Path(__file__).parents[3] / "supabase" / "seed" / "essays.json").read_text(encoding="utf-8"))
ALL = [EssaySummary.model_validate(e) for e in SEED]


async def test_list_comes_from_db_without_bodies(client):
    items = (await client.get("/essays")).json()
    assert len(items) == len(SEED) > 100
    assert all("body" not in e for e in items)
    assert [e["id"] for e in items] == sorted(e["id"] for e in SEED)


async def test_get_by_id_returns_body_and_references(client):
    src = next(e for e in SEED if e["references"])
    one = (await client.get(f"/essays/{src['id']}")).json()
    assert one["body"] == src["body"] and one["references"] == src["references"]
    assert one["majors"] == src["majors"] and one["school"] == src["school"]
    missing = await client.get("/essays/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "ESSAY_NOT_FOUND"


async def test_recommended_puts_bachelor_first(client, user):
    await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    recs = (await client.get("/me/essays/recommended", headers=user["headers"])).json()
    assert recs and recs[0]["essay"]["level"] == "bachelor"
    assert all(r["reasons"] for r in recs)


def _profile(majors: list[str]) -> Profile:
    return Profile.model_validate({**{k: v for k, v in PROFILE.items() if k != "initial_achievements"},
                                   "majors": majors, "created_at": "2026-09-01T00:00:00"})


def test_favorite_university_ranks_higher_and_is_deterministic():
    profile = _profile(["social_sciences"])
    base = essays.recommend_essays(ALL, profile, [], [], {}, {})
    with_fav = essays.recommend_essays(ALL, profile, ["ucl"], [], {"ucl": "UCL"}, {})
    assert with_fav[0].essay.university_id == "ucl"
    assert any("UCL" in reason for reason in with_fav[0].reasons)
    assert base == essays.recommend_essays(ALL, profile, [], [], {}, {})


def test_major_match_counts():
    recs = essays.recommend_essays(ALL, _profile(["biology"]), [], [], {}, {"biology": "Биология"})
    assert "biology" in recs[0].essay.majors
    assert any("Биология" in reason for reason in recs[0].reasons)
