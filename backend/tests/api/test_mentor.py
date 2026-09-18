"""Mentor chat with a scripted model: no network, the tool loop and proposal flow are real."""
import json
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.llm import mentor_model
from app.llm.mentor_model import ModelTurn, ToolCall

from .conftest import token_for
from .test_api import PROFILE


class Script:
    """Replays model turns in order and records what the model was shown."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.systems: list[str] = []
        self.histories: list[list] = []

    async def __call__(self, system, history, tools):
        self.systems.append(system)
        self.histories.append(list(history))
        turn = self.turns.pop(0)
        return turn(history) if callable(turn) else turn


@pytest.fixture
def script(monkeypatch):
    def install(*turns):
        s = Script(*turns)
        monkeypatch.setattr(mentor_model, "model_step", s)
        return s
    return install


def last_tool_results(history):
    return dict(history[-1]["results"])


async def setup(client, h):
    await client.put("/me/profile", json=PROFILE, headers=h)
    await client.put("/me/favorites/purdue", headers=h)
    sug = (await client.get("/me/roadmap/suggestions", headers=h)).json()
    return next(s for s in sug if s["id"].startswith("act:"))


async def test_fallback_without_llm_key(client, user):
    h = user["headers"]
    await setup(client, h)
    r = (await client.post("/ai/mentor", json={"text": "Что делать?"}, headers=h)).json()
    user_msg, reply = r["messages"]
    assert user_msg["role"] == "user" and reply["role"] == "assistant"
    assert reply["generated"] is False and "недоступен" in reply["text"] and reply["actions"] == []
    assert len((await client.get("/ai/mentor", headers=h)).json()) == 2


async def test_context_has_plan_and_suggestions(client, user, script):
    h = user["headers"]
    act = await setup(client, h)
    s = script(ModelTurn(text="Привет"))
    await client.post("/ai/mentor", json={"text": "Привет"}, headers=h)
    ctx = json.loads(s.systems[0].split("CONTEXT:\n", 1)[1])
    assert act["id"] in [x["id"] for x in ctx["suggestions"]]
    assert ctx["favorites"] and ctx["profile"]["best_scores"]["SAT"] == 1380
    assert all("chance" in r and "tier" in r for r in ctx["recommendations"])


async def test_proposal_is_applied_only_on_confirmation(client, user, script):
    h = user["headers"]
    act = await setup(client, h)
    s = script(
        ModelTurn(calls=[ToolCall("get_university", {"university_id": "purdue"}),
                         ToolCall("propose_add_suggestion", {"suggestion_id": act["id"]})]),
        ModelTurn(text="Предлагаю добавить активность — подтвердите ниже."),
    )
    reply = (await client.post("/ai/mentor", json={"text": "Что добавить?"}, headers=h)).json()["messages"][1]
    results = last_tool_results(s.histories[1])
    assert results["get_university"]["name"].startswith("Purdue") and "is_demo" in results["get_university"]["ielts_min"]
    assert results["propose_add_suggestion"]["ok"]
    assert reply["generated"] and [a["status"] for a in reply["actions"]] == ["pending"]
    assert act["title"] in reply["actions"][0]["summary"]
    assert (await client.get("/me/roadmap", headers=h)).json()["steps"] == []  # nothing changed yet

    url = f"/ai/mentor/{reply['id']}/actions/0"
    applied = (await client.post(url, json={"apply": True}, headers=h)).json()
    assert applied["message"]["actions"][0]["status"] == "applied"
    assert [x["source_key"] for x in applied["roadmap"]["steps"]] == [act["id"]]
    assert (await client.post(url, json={"apply": True}, headers=h)).status_code == 409

    other = {"Authorization": f"Bearer {token_for(str(uuid4()))}"}
    assert (await client.post(url, json={"apply": False}, headers=other)).status_code == 404


async def test_update_dismiss_and_invalid_proposals(client, user, script):
    h = user["headers"]
    act = await setup(client, h)
    step = (await client.post("/me/roadmap/items", json={"suggestion_id": act["id"]}, headers=h)).json()["steps"][0]
    new_due = (date.today() + timedelta(days=40)).isoformat()
    s = script(
        ModelTurn(calls=[
            ToolCall("propose_update_step", {"step_id": step["id"], "due_date": new_due}),
            ToolCall("propose_update_step", {"step_id": str(uuid4()), "done": True}),        # not in the plan
            ToolCall("propose_add_step", {"title": "Прошлое", "kind": "activity", "due_date": "2020-01-01"}),
            ToolCall("propose_delete_step", {"step_id": step["id"]}),
        ]),
        ModelTurn(text="Готово, подтвердите изменения."),
    )
    reply = (await client.post("/ai/mentor", json={"text": "Перенеси"}, headers=h)).json()["messages"][1]
    results = s.histories[1][-1]["results"]
    assert "error" in results[1][1] and "error" in results[2][1]
    assert [a["type"] for a in reply["actions"]] == ["update_step", "delete_step"]

    base = f"/ai/mentor/{reply['id']}/actions"
    rm = (await client.post(f"{base}/0", json={"apply": True}, headers=h)).json()["roadmap"]
    assert rm["steps"][0]["due_date"] == new_due
    dismissed = (await client.post(f"{base}/1", json={"apply": False}, headers=h)).json()
    assert dismissed["message"]["actions"][1]["status"] == "dismissed" and dismissed["roadmap"] is None
    assert len((await client.get("/me/roadmap", headers=h)).json()["steps"]) == 1


async def test_chance_percent_is_sanitized_and_reset_clears(client, user, script):
    h = user["headers"]
    await setup(client, h)
    script(ModelTurn(text="Ваш шанс в MIT около 15%. Готовьтесь к SAT."))
    reply = (await client.post("/ai/mentor", json={"text": "Какой шанс?"}, headers=h)).json()["messages"][1]
    assert "15%" not in reply["text"] and "Процентов шанса мы не даём" in reply["text"]
    assert (await client.post("/me/reset", headers=h)).json() == {"ok": True}
    await client.put("/me/profile", json=PROFILE, headers=h)
    assert (await client.get("/ai/mentor", headers=h)).json() == []


def test_plain_text_strips_markdown():
    from app.services.mentor import plain_text
    assert plain_text("## Итог\n* **SAT** 1200\n- __IELTS__ 6.5") == "Итог\n• SAT 1200\n• IELTS 6.5"
