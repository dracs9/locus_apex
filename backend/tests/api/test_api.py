from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select

from app import db
from app.schemas import RecommendationResult, Snapshot
from app.services import snapshots

from .conftest import token_for

PROFILE = {
    "grade": 11, "gpa5": 4.6, "majors": ["cs"], "countries": ["US", "UK", "NL"], "budget_per_year_usd": 50000,
    "needs_aid": True, "intake_year": 2028, "priorities": {"cost": 0.5, "prestige": 0.5, "location": 0.5, "aid": 0.5},
    "initial_achievements": [{"type": "SAT", "score": 1380, "date": "2026-08-01", "status": "done"},
                             {"type": "IELTS", "score": 7.0, "date": "2026-05-01", "status": "done"}],
}


async def count(table) -> int:
    async with db.get_engine().connect() as conn:
        return (await conn.execute(select(func.count()).select_from(table))).scalar_one()


async def test_health_and_catalog(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    unis = (await client.get("/catalog/universities")).json()
    assert len(unis) >= 15
    assert (await client.get("/catalog/universities/mit")).json()["name"].startswith("Massachusetts")
    missing = await client.get("/catalog/universities/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "UNIVERSITY_NOT_FOUND"
    assert len((await client.get("/catalog/majors")).json()) == 10


async def test_me_requires_token(client):
    r = await client.get("/me/profile")
    assert r.status_code == 401 and "error" in r.json()
    r = await client.get("/me/profile", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_put_profile_returns_diff(client, user):
    first = await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["diff"] is None and len(body["result"]["recs"]) >= 3 and body["roadmap"]["steps"] == []

    cheaper = {**PROFILE, "budget_per_year_usd": 20000, "initial_achievements": []}
    second = (await client.put("/me/profile", json=cheaper, headers=user["headers"])).json()
    assert second["diff"] is not None
    assert second["diff"]["removed"]
    assert "Бюджет" in second["diff"]["cause"]
    latest = (await client.get("/me/changes/latest", headers=user["headers"])).json()
    assert latest["diff"]["removed"] == second["diff"]["removed"]
    assert len((await client.get("/me/profile", headers=user["headers"])).json()["achievements"]) == 2


async def test_user_isolation(client, user):
    await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    ach = (await client.get("/me/profile", headers=user["headers"])).json()["achievements"][0]

    other = {"Authorization": f"Bearer {token_for(str(uuid4()))}"}
    assert (await client.get("/me/profile", headers=other)).status_code == 404
    assert (await client.get("/me/recommendations", headers=other)).status_code == 404
    assert (await client.delete(f"/me/achievements/{ach['id']}", headers=other)).status_code == 404
    assert len((await client.get("/me/profile", headers=user["headers"])).json()["achievements"]) == 2


async def test_preview_saves_nothing(client, user):
    await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    profile = (await client.get("/me/profile", headers=user["headers"])).json()
    tables = (db.snapshots, db.profiles, db.achievements, db.favorites, db.roadmap_items, db.mentor_messages)
    before = [await count(t) for t in tables]
    r = await client.post("/preview", json={"profile": profile,
                                            "priorities_override": {"cost": 1, "prestige": 0, "location": 0, "aid": 0}})
    assert r.status_code == 200 and r.json()["recs"]
    assert before == [await count(t) for t in tables]


async def test_achievement_flow_updates_route(client, user):
    await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    r = (await client.post("/me/achievements", json={"type": "SAT", "score": 1560, "date": "2026-09-01", "status": "done"},
                           headers=user["headers"])).json()
    assert r["diff"] is not None
    assert r["diff"]["tier_changed"] or r["diff"]["gaps_closed"]
    assert "SAT 1380 → 1560" in r["diff"]["cause"]
    history = (await client.get("/me/chance-history?ids=purdue,mit", headers=user["headers"])).json()
    assert len(history) >= 2 and set(history[-1]["chance_by_uni"]) == {"purdue", "mit"}


async def test_added_achievement_keeps_snapshot_reusable(client, user):
    """POST builds the post-insert profile in memory rather than re-reading it.

    profile_hash covers the achievement list *in order*, and the DB orders by
    (date, created_at, id). The date here falls between the two seeded ones (2026-05-01 and
    2026-08-01), so appending instead of inserting in date order yields a different hash — and
    then every later read misses the snapshot and recomputes, which shows up as a fresh
    computed_at.
    """
    await client.put("/me/profile", json=PROFILE, headers=user["headers"])
    posted = (await client.post("/me/achievements",
                                json={"type": "OLYMPIAD", "title": "Мат. олимпиада", "level": "national",
                                      "date": "2026-06-15", "status": "done"},
                                headers=user["headers"])).json()
    first = (await client.get("/me/recommendations", headers=user["headers"])).json()
    second = (await client.get("/me/recommendations", headers=user["headers"])).json()
    assert posted["result"]["computed_at"] == first["computed_at"] == second["computed_at"]


async def test_snapshot_save_prunes_to_keep_last(user):
    """save() prunes with a DELETE over a subselect instead of fetching the ids first.

    Worth a test because the subselect uses OFFSET without LIMIT, which SQLite only accepts
    via its `LIMIT -1 OFFSET n` rendering, and because nothing else here ever exceeds 50 rows.
    """
    uid = UUID(user["id"])
    empty = RecommendationResult(recs=[], excluded=[], suggestions=[], computed_at=datetime(2026, 9, 1, 12, 0))
    async with db.get_engine().begin() as conn:
        for i in range(snapshots.KEEP_LAST + 5):
            await conn.execute(insert(db.snapshots).values(
                id=uuid4(), user_id=uid, at=datetime(2026, 1, 1, 0, 0) + timedelta(minutes=i),
                result=empty.model_dump(mode="json"), roadmap_step_ids=[], profile_hash=f"h{i}", cause="seed"))

    snap = Snapshot(id=uuid4(), at=datetime(2026, 9, 2, 12, 0), result=empty, roadmap_step_ids=[],
                    profile_hash="newest", cause="test")
    async with db.new_session() as session:
        await snapshots.save(session, uid, snap, None)
        await session.commit()
        mine = (await session.execute(select(func.count()).select_from(db.snapshots)
                                      .where(db.snapshots.c.user_id == uid))).scalar_one()
        kept = (await session.execute(select(db.snapshots.c.profile_hash)
                                      .where(db.snapshots.c.user_id == uid)
                                      .order_by(db.snapshots.c.at.desc()).limit(1))).scalar_one()
    assert mine == snapshots.KEEP_LAST
    assert kept == "newest"  # the prune drops the oldest, not the row just written


async def test_plan_is_built_from_suggestions_and_own_steps(client, user):
    h = user["headers"]
    await client.put("/me/profile", json=PROFILE, headers=h)
    r = (await client.put("/me/favorites/purdue", headers=h)).json()
    assert "Purdue" in r["diff"]["cause"] and r["roadmap"]["steps"] == []  # nothing is generated into the plan

    sug = (await client.get("/me/roadmap/suggestions", headers=h)).json()
    assert [s["id"] for s in sug if s["kind"] == "application"] == ["apply:purdue:EA"]
    assert any(s["id"].startswith("act:") for s in sug) and all(s["why"]["text"] for s in sug)

    added = await client.post("/me/roadmap/items", json={"suggestion_id": "apply:purdue:EA"}, headers=h)
    assert added.status_code == 201
    [apply] = added.json()["steps"]
    assert apply["source_key"] == "apply:purdue:EA" and apply["university_ids"] == ["purdue"]
    assert "apply:purdue:EA" not in [s["id"] for s in (await client.get("/me/roadmap/suggestions", headers=h)).json()]
    dup = await client.post("/me/roadmap/items", json={"suggestion_id": "apply:purdue:EA"}, headers=h)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "STEP_EXISTS"
    gone = await client.post("/me/roadmap/items", json={"suggestion_id": "act:nope"}, headers=h)
    assert gone.status_code == 404

    custom = (await client.post("/me/roadmap/items", json={"title": "Сходить на день открытых дверей",
                                                           "kind": "activity", "due_date": "2026-12-01",
                                                           "note": "взять друга"}, headers=h)).json()
    mine = next(s for s in custom["steps"] if s["source_key"] is None)
    assert mine["note"] == "взять друга" and len(custom["steps"]) == 2
    bad = await client.post("/me/roadmap/items", json={"title": "без даты", "kind": "activity"}, headers=h)
    assert bad.status_code == 422

    rm = (await client.patch(f"/me/roadmap/items/{mine['id']}", json={"done": True, "due_date": "2026-11-20",
                                                                     "title": "День открытых дверей"}, headers=h)).json()
    step = next(s for s in rm["steps"] if s["id"] == mine["id"])
    assert step["done"] and step["due_date"] == "2026-11-20" and step["title"] == "День открытых дверей"
    assert rm["progress"] == 0.5

    other = {"Authorization": f"Bearer {token_for(str(uuid4()))}"}
    assert (await client.patch(f"/me/roadmap/items/{mine['id']}", json={"done": False}, headers=other)).status_code == 404
    assert (await client.delete(f"/me/roadmap/items/{mine['id']}", headers=other)).status_code == 404

    ics = await client.get("/me/roadmap.ics", headers=h)
    assert ics.status_code == 200 and "BEGIN:VCALENDAR" in ics.text and "Purdue" in ics.text
    rm = (await client.delete(f"/me/roadmap/items/{mine['id']}", headers=h)).json()
    assert [s["id"] for s in rm["steps"]] == [apply["id"]]
    assert (await client.delete(f"/me/roadmap/items/{mine['id']}", headers=h)).status_code == 404


async def test_demo_reset_and_ai_fallbacks(client, user):
    r = (await client.post("/me/demo", headers=user["headers"])).json()
    tiers = {x["tier"] for x in r["result"]["recs"]}
    assert len(r["result"]["recs"]) >= 3 and len(tiers) >= 2
    assert all(len(x["reasons"]) >= 2 for x in r["result"]["recs"])
    p = (await client.post("/ai/passport", headers=user["headers"])).json()
    assert p["generated"] is False and len(p["strengths"]) == 3 and len(p["constraints"]) == 2
    e = (await client.post("/ai/explain", json={"university_id": "mit"}, headers=user["headers"])).json()
    assert e["generated"] is False and e["summary"]
    assert r["roadmap"]["steps"], "the demo shows a ready plan"
    sug = (await client.get("/me/roadmap/suggestions", headers=user["headers"])).json()
    steps = [s["id"] for s in r["roadmap"]["steps"]][:2] + [s["id"] for s in sug][:2]
    t = (await client.post("/ai/roadmap-text", json={"step_ids": steps}, headers=user["headers"])).json()
    assert [i["id"] for i in t["items"]] == steps and all(i["description"] for i in t["items"])
    assert (await client.post("/me/reset", headers=user["headers"])).json() == {"ok": True}
    assert (await client.get("/me/profile", headers=user["headers"])).status_code == 404


async def test_grade_nine_ib_interests_and_zero_budget_persist(client, user):
    from app.engine.interests import questionnaire
    answers = {q['id']: 3 for q in questionnaire()['questions']}
    payload = {**PROFILE, 'grade': 9, 'gpa5': None, 'academic_record': {'scale': 'ib8', 'value': 7.5},
               'holland': {'version': 'applyra-riasec-v1', 'answers': answers}, 'budget_per_year_usd': 0}
    response = await client.put('/me/profile', json=payload, headers=user['headers'])
    assert response.status_code == 200, response.text
    saved = (await client.get('/me/profile', headers=user['headers'])).json()
    assert saved['grade'] == 9 and saved['budget_per_year_usd'] == 0
    assert saved['academic_record'] == payload['academic_record']
    assert saved['holland']['answers'] == answers
    assert (await client.get('/me/recommendations', headers=user['headers'])).status_code == 200
    invalid = {**payload, 'holland': {'answers': {}}}
    assert (await client.put('/me/profile', json=invalid, headers=user['headers'])).status_code == 422
    assert (await client.get('/me/profile', headers=user['headers'])).json()['holland'] == saved['holland']
