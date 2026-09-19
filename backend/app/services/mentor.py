"""AI mentor: builds the student's context, runs the Gemini tool loop, and records proposed plan changes.

Read tools retrieve facts from the catalog (with sources and demo flags). Proposal tools only validate and
record an action; the plan changes when the student applies it (`apply_action`).
"""
import json
import re
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import text
from app.engine.interests import scores
from app.engine.normalize import best_ielts, best_score, done_achievements, projected_deadlines
from app.llm import mentor_model, prompts
from app.llm.mentor_model import History, ToolCall
from app.schemas import Profile, Roadmap, StepIn, StepPatch, Suggestion, University
from app.schemas.mentor import MentorAction, MentorMessage

from . import catalog, compute, plan, profiles

MAX_ROUNDS = 4
MAX_ACTIONS = 4
HISTORY_MESSAGES = 12
MAX_AHEAD_DAYS = 730
KIND_RU = {"exam": "экзамен", "document": "документы", "academic": "учёба", "activity": "активность",
           "application": "заявка"}
CHANCE_PERCENT = re.compile(r"(шанс|вероятн)[^.\n]{0,60}?\d+\s?%|\d+\s?%[^.\n]{0,60}?(шанс|вероятн)", re.I)

TOOLS: list[dict] = [
    {"name": "get_university", "description": "Факты о вузе из каталога: стоимость, IELTS, SAT, дедлайны, финпомощь, "
     "требования, документы — с источником и флагом is_demo; и категория вуза для ученика, если он в подборке.",
     "parameters": {"type": "OBJECT", "properties": {"university_id": {"type": "STRING"}}, "required": ["university_id"]}},
    {"name": "find_universities", "description": "Поиск вузов в каталоге по стране (код: US, UK, DE, NL, KR, SG, CA, HK, CN, IT, JP, CH, FR, AU, IE, SE, ES), "
     "направлению (id: cs, engineering, economics, business, math, physics, biology, medicine, design, social_sciences) "
     "и максимальной стоимости в год (USD). Возвращает до 10 вузов.",
     "parameters": {"type": "OBJECT", "properties": {"country": {"type": "STRING"}, "major": {"type": "STRING"},
                                                    "max_cost": {"type": "INTEGER"}}}},
    {"name": "propose_add_suggestion", "description": "Предложить добавить в план рекомендацию из CONTEXT.suggestions.",
     "parameters": {"type": "OBJECT", "properties": {"suggestion_id": {"type": "STRING"},
                                                    "due_date": {"type": "STRING", "description": "ГГГГ-ММ-ДД, необязательно"}},
                    "required": ["suggestion_id"]}},
    {"name": "propose_add_step", "description": "Предложить добавить в план свой шаг.",
     "parameters": {"type": "OBJECT", "properties": {
         "title": {"type": "STRING"},
         "kind": {"type": "STRING", "enum": ["exam", "document", "academic", "activity", "application"]},
         "due_date": {"type": "STRING", "description": "ГГГГ-ММ-ДД"},
         "note": {"type": "STRING"}}, "required": ["title", "kind", "due_date"]}},
    {"name": "propose_update_step", "description": "Предложить изменить шаг плана (id из CONTEXT.plan): название, срок, "
     "заметку или отметить выполненным.",
     "parameters": {"type": "OBJECT", "properties": {
         "step_id": {"type": "STRING"}, "title": {"type": "STRING"},
         "due_date": {"type": "STRING", "description": "ГГГГ-ММ-ДД"}, "note": {"type": "STRING"},
         "done": {"type": "BOOLEAN"}}, "required": ["step_id"]}},
    {"name": "propose_delete_step", "description": "Предложить удалить шаг из плана (id из CONTEXT.plan).",
     "parameters": {"type": "OBJECT", "properties": {"step_id": {"type": "STRING"}}, "required": ["step_id"]}},
]


def plain_text(s: str) -> str:
    """The chat renders plain text: drop Markdown emphasis and headings, turn list markers into bullets."""
    s = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)
    return re.sub(r"^\s*[*-]\s+", "• ", s, flags=re.M).strip()


def _d(value: date) -> str:
    return f"{value:%d.%m.%Y}"


def holland_code(profile: Profile) -> str | None:
    if profile.holland is None:
        return None
    values = scores(profile.holland)
    if max(values.values()) == min(values.values()):
        return None
    return "".join(sorted(values, key=lambda c: (-values[c], c))[:3])


def university_facts(uni: University, profile: Profile, rec=None) -> dict:
    def fact(s, fmt=lambda v: v):
        return {"value": fmt(s.value) if s.value is not None else "не опубликовано", "is_demo": s.is_demo,
                "source_url": s.source_url}
    return {
        "id": uni.id, "name": uni.name, "country": text.country(uni.country), "city": uni.city, "website": uni.website,
        "acceptance_rate": fact(uni.acceptance_rate, lambda v: f"≈{round(v * 100)} из 100 поступающих"),
        "sat_25_75": fact(uni.sat, lambda v: f"{v.p25}–{v.p75}"),
        "gpa_avg_4": fact(uni.gpa_avg),
        "ielts_min": fact(uni.ielts_min),
        "cost_per_year": fact(uni.cost_per_year_usd, text.money),
        "intl_aid": fact(uni.intl_aid, lambda v: text.AID_RU.get(v, v)),
        "deadlines": [{"date": d.isoformat(), "type": text.DEADLINE_RU[dl.type], "is_demo": demo, "source_url": src}
                      for d, dl, demo, src in projected_deadlines(uni, profile.intake_year)],
        "extra_requirements": uni.extra_requirements,
        "documents": uni.documents,
        "majors": uni.majors,
        "for_student": ({"tier": rec.tier, "chance": rec.chance, "reasons": [r.text for r in rec.reasons]}
                        if rec else "не в подборке ученика"),
    }


class Mentor:
    """One mentor turn for one student. All data access is scoped to `user_id`."""

    def __init__(self, session: AsyncSession, user_id: UUID, profile: Profile, today: date):
        self.session, self.user_id, self.profile, self.today = session, user_id, profile, today
        self.actions: list[MentorAction] = []

    async def load(self) -> None:
        self.unis = {u.id: u for u in await catalog.universities(self.session)}
        self.major_names = await catalog.major_names(self.session)
        self.result = await compute.current_result(self.session, self.user_id, self.profile)
        self.roadmap: Roadmap = await compute.roadmap_for(self.session, self.user_id)
        self.suggestions: list[Suggestion] = await compute.suggestions_for(self.session, self.user_id, self.profile,
                                                                           self.result)
        self.favorites = await profiles.favorite_ids(self.session, self.user_id)

    def context(self) -> dict:
        p = self.profile
        conflicts = {c.step_id: c.message for c in self.roadmap.conflicts}
        return {
            "today": self.today.isoformat(),
            "profile": {
                "grade": p.grade, "intake_year": p.intake_year,
                "academic": p.academic_record.model_dump() if p.academic_record else {"scale": "5", "value": p.gpa5},
                "majors": [self.major_names.get(m, m) for m in p.majors],
                "countries": [text.country(c) for c in p.countries],
                "budget_per_year": text.money(p.budget_per_year_usd), "needs_aid": p.needs_aid,
                "best_scores": {"SAT": best_score(p, "SAT"), "IELTS": best_ielts(p), "TOEFL": best_score(p, "TOEFL")},
                "achievements": [{"type": a.type, "title": a.title, "level": a.level, "date": a.date.isoformat()}
                                 for a in done_achievements(p)],
                "planned": [{"type": a.type, "date": a.date.isoformat()} for a in p.achievements if a.status == "planned"],
                "holland_code": holland_code(p),
                "priorities": p.priorities.model_dump(),
            },
            "recommendations": [
                {"id": r.university_id, "name": self.unis[r.university_id].name if r.university_id in self.unis else r.university_id,
                 "tier": r.tier, "chance": r.chance, "reasons": [x.text for x in r.reasons]}
                for r in self.result.recs[:10]],
            "recommendations_total": len(self.result.recs),
            "excluded_total": len(self.result.excluded),
            "engine_suggestions": self.result.suggestions,
            "favorites": [self.unis[i].name if i in self.unis else i for i in self.favorites],
            "plan": [{"id": s.id, "title": s.title, "kind": s.kind, "due_date": s.due_date.isoformat(), "done": s.done,
                      "note": s.note, "conflict": conflicts.get(s.id)} for s in self.roadmap.steps],
            "suggestions": [{"id": s.id, "title": s.title, "kind": s.kind, "why": s.why.text,
                             "suggested_due": s.suggested_due.isoformat()} for s in self.suggestions[:15]],
        }

    # --- tools -------------------------------------------------------------------------------------------

    async def run(self, call: ToolCall) -> dict:
        handler = getattr(self, f"tool_{call.name}", None)
        if handler is None:
            return {"error": f"Нет инструмента {call.name}"}
        try:
            return await handler(**call.args)
        except TypeError as e:
            return {"error": f"Неверные аргументы: {e}"}

    async def tool_get_university(self, university_id: str) -> dict:
        uni = self.unis.get(university_id) or next(
            (u for u in self.unis.values() if u.name.lower() == university_id.lower()), None)
        if uni is None:
            return {"error": "Вуза нет в каталоге", "hint": "используйте find_universities"}
        rec = next((r for r in self.result.recs if r.university_id == uni.id), None)
        return university_facts(uni, self.profile, rec)

    async def tool_find_universities(self, country: str | None = None, major: str | None = None,
                                     max_cost: int | None = None) -> dict:
        found = [u for u in self.unis.values()
                 if (not country or u.country == country.upper())
                 and (not major or major in u.majors)
                 and (not max_cost or (u.cost_per_year_usd.value is not None and u.cost_per_year_usd.value <= max_cost))]
        found.sort(key=lambda u: (u.world_rank, u.id))
        return {"universities": [{"id": u.id, "name": u.name, "country": text.country(u.country)} for u in found[:10]],
                "total": len(found)}

    def _due(self, raw: str | None) -> date | None | dict:
        if raw in (None, ""):
            return None
        try:
            d = date.fromisoformat(str(raw)[:10])
        except ValueError:
            return {"error": "Дата должна быть в формате ГГГГ-ММ-ДД"}
        if d < self.today or d > self.today + timedelta(days=MAX_AHEAD_DAYS):
            return {"error": f"Дата должна быть между {self.today.isoformat()} и двумя годами вперёд"}
        return d

    def _propose(self, type_: str, summary: str, args: dict) -> dict:
        if len(self.actions) >= MAX_ACTIONS:
            return {"error": "Слишком много предложений за один ответ"}
        if any(a.type == type_ and a.args == args for a in self.actions):
            return {"ok": True, "note": "уже предложено"}
        self.actions.append(MentorAction(type=type_, summary=summary, args=args))
        return {"ok": True, "proposed": summary, "note": "Ученик должен подтвердить кнопкой «Применить»"}

    def _step(self, step_id: str):
        return next((s for s in self.roadmap.steps if s.id == step_id), None)

    async def tool_propose_add_suggestion(self, suggestion_id: str, due_date: str | None = None) -> dict:
        s = next((s for s in self.suggestions if s.id == suggestion_id), None)
        if s is None:
            return {"error": "Такой рекомендации нет в CONTEXT.suggestions (или она уже в плане)"}
        due = self._due(due_date)
        if isinstance(due, dict):
            return due
        due = due or s.suggested_due
        return self._propose("add_suggestion", f"Добавить в план: «{s.title}» до {_d(due)}",
                             {"suggestion_id": s.id, "due_date": due.isoformat()})

    async def tool_propose_add_step(self, title: str, kind: str, due_date: str, note: str | None = None) -> dict:
        due = self._due(due_date)
        if not isinstance(due, date):
            return due or {"error": "Укажите дату"}
        try:
            body = StepIn(title=title.strip(), kind=kind, due_date=due, note=note or None)
        except ValidationError as e:
            return {"error": f"Неверный шаг: {e.errors()[0]['msg']}"}
        return self._propose("add_step", f"Добавить свой шаг: «{body.title}» ({KIND_RU[body.kind]}) до {_d(due)}",
                             body.model_dump(mode="json", exclude={"suggestion_id"}, exclude_none=True))

    async def tool_propose_update_step(self, step_id: str, title: str | None = None, due_date: str | None = None,
                                       note: str | None = None, done: bool | None = None) -> dict:
        step = self._step(step_id)
        if step is None:
            return {"error": "Такого шага нет в плане ученика"}
        due = self._due(due_date)
        if isinstance(due, dict):
            return due
        try:
            patch = StepPatch(title=title, due_date=due, note=note, done=done)
        except ValidationError as e:
            return {"error": f"Неверные значения: {e.errors()[0]['msg']}"}
        values = patch.model_dump(mode="json", exclude_none=True)
        if not values:
            return {"error": "Нечего менять"}
        parts = []
        if "title" in values:
            parts.append(f"название → «{values['title']}»")
        if "due_date" in values:
            parts.append(f"срок → {_d(due)}")
        if "note" in values:
            parts.append("новая заметка")
        if "done" in values:
            parts.append("отметить выполненным" if values["done"] else "вернуть в работу")
        return self._propose("update_step", f"Изменить «{step.title}»: {', '.join(parts)}",
                             {"step_id": step_id, "values": values})

    async def tool_propose_delete_step(self, step_id: str) -> dict:
        step = self._step(step_id)
        if step is None:
            return {"error": "Такого шага нет в плане ученика"}
        return self._propose("delete_step", f"Удалить из плана: «{step.title}»", {"step_id": step_id})

    # --- the turn --------------------------------------------------------------------------------------------

    def fallback(self) -> str:
        nxt = next((s for s in self.roadmap.steps if s.id == self.roadmap.next_step_id), None)
        tip = (f" Ближайший шаг вашего плана: «{nxt.title}» до {_d(nxt.due_date)}." if nxt
               else " Загляните в «План» — там рекомендации, которые можно добавить.")
        return "ИИ-ментор сейчас недоступен." + tip

    async def reply(self, past: list[MentorMessage], user_text: str) -> tuple[str, bool]:
        """Returns (text, generated). Proposed actions are collected in self.actions."""
        system = prompts.MENTOR + json.dumps(self.context(), ensure_ascii=False, default=str)
        history: History = []
        for m in past[-HISTORY_MESSAGES:]:
            body = m.text
            if m.actions:
                body += "\n[Предложения: " + "; ".join(f"{a.summary} — {a.status}" for a in m.actions) + "]"
            history.append({"role": "user" if m.role == "user" else "model", "text": body})
        history.append({"role": "user", "text": user_text})

        turn = None
        for _ in range(MAX_ROUNDS):
            turn = await mentor_model.model_step(system, history, TOOLS)
            if turn is None:
                break
            if not turn.calls:
                break
            history.append({"role": "model", "calls": turn.calls, "raw": turn.raw})
            history.append({"role": "tool", "results": [(c.name, await self.run(c)) for c in turn.calls]})

        if turn is None:
            return self.fallback(), False
        reply = turn.text if not turn.calls else ""
        if not reply:
            reply = ("Я подготовил предложения для плана — посмотрите ниже и подтвердите нужные."
                     if self.actions else "Не получилось сформулировать ответ. Попробуйте спросить иначе.")
        reply = plain_text(reply)
        if CHANCE_PERCENT.search(reply):
            reply = re.sub(r"\d+\s?%", "—", reply) + "\n\n(Процентов шанса мы не даём — смотрите категорию вуза.)"
        return reply, True


async def apply_action(session: AsyncSession, user_id: UUID, profile: Profile, action: MentorAction) -> None:
    """Executes a proposed change through the same code paths as the plan endpoints. Raises plan.PlanError."""
    a = action.args
    if action.type == "add_suggestion":
        await plan.add_from_suggestion(session, user_id, profile, a["suggestion_id"],
                                       due_date=date.fromisoformat(a["due_date"]) if a.get("due_date") else None)
    elif action.type == "add_step":
        await plan.add_custom(session, user_id, title=a.get("title"), kind=a.get("kind"),
                              due_date=date.fromisoformat(a["due_date"]), note=a.get("note"))
    elif action.type == "update_step":
        values: dict[str, Any] = dict(a["values"])
        if "due_date" in values:
            values["due_date"] = date.fromisoformat(values["due_date"])
        await plan.patch(session, user_id, UUID(a["step_id"]), values)
    elif action.type == "delete_step":
        await plan.delete(session, user_id, UUID(a["step_id"]))
