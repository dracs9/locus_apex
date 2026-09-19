from app.schemas import Profile
from app.services import essays

from .test_api import PROFILE


async def test_list_has_no_bodies_and_get_by_id(client):
    items = (await client.get("/essays")).json()
    assert len(items) == len(essays.load()) > 100
    assert all("body" not in e for e in items)
    one = (await client.get(f"/essays/{items[0]['id']}")).json()
    assert one["body"] and one["id"] == items[0]["id"]
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
    base = essays.recommend_essays(essays.summaries(), profile, [], [], {}, {})
    with_fav = essays.recommend_essays(essays.summaries(), profile, ["ucl"], [], {"ucl": "UCL"}, {})
    assert with_fav[0].essay.university_id == "ucl"
    assert any("UCL" in reason for reason in with_fav[0].reasons)
    assert base == essays.recommend_essays(essays.summaries(), profile, [], [], {}, {})


def test_major_match_counts():
    recs = essays.recommend_essays(essays.summaries(), _profile(["biology"]), [], [], {}, {"biology": "Биология"})
    assert "biology" in recs[0].essay.majors
    assert any("Биология" in reason for reason in recs[0].reasons)
