"""Roadmap (§8.7, reworked): the engine suggests steps, the student builds the plan from them.

`suggest_actions` turns profile gaps, target universities and an activity catalog into suggestions with a
reason each. `build_roadmap` orders the student's own stored steps and finds conflicts. Both are pure.
"""
import json
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from app.schemas import Conflict, Profile, Recommendation, Roadmap, RoadmapStep, Suggestion, SuggestionWhy, University

from . import config, text
from .interests import questionnaire, scores
from .normalize import application_deadline, best_ielts, best_score, done_achievements, profile_gpa4

EXAM_BUFFER_DAYS = 3  # safety margin between exam result and deadline

# document id -> (title, days before the application deadline)
DOCUMENTS = {
    "transcript": ("Получить выписку оценок (транскрипт) с переводом", 45),
    "recommendations": ("Попросить учителей о рекомендательных письмах", 30),
    "essay": ("Написать эссе для заявки", 21),
    "personal_statement": ("Написать Personal Statement", 21),
    "motivation_letter": ("Написать мотивационное письмо", 21),
    "cv": ("Подготовить CV", 30),
    "portfolio": ("Собрать портфолио", 45),
    "financial_docs": ("Собрать финансовые документы (CSS Profile / справки о доходах)", 14),
    "passport": ("Проверить загранпаспорт (срок действия)", 60),
}
PRIORITY = {"application": 5, "exam": 4, "document": 3, "academic": 2, "activity": 1}
ACADEMIC_LEAD_DAYS = 90
MAX_ACTIVITY_SUGGESTIONS = 8
MIN_ACTIVITY_LEAD_DAYS = 14   # a catalog suggestion is never due sooner than this
ACTIVITY_DEADLINE_MARGIN = 30  # ...and should be finished this long before the earliest application deadline
ENGLISH_PRACTICE_ENOUGH = 7.0  # IELTS level at which extra English practice is no longer suggested


@cache
def exams() -> dict:
    return json.loads((Path(__file__).parent.parent / "data" / "exams.json").read_text(encoding="utf-8"))


@cache
def activities() -> list[dict]:
    return json.loads((Path(__file__).parent.parent / "data" / "activities.json").read_text(encoding="utf-8"))


def _targets(favorite_ids: list[str], recs: list[Recommendation], by_id: dict[str, University]) -> list[University]:
    favs = [by_id[i] for i in sorted(set(favorite_ids)) if i in by_id]
    if favs:
        return favs
    # fallback: the best university of each tier, then the best remaining ones
    ranked = sorted(recs, key=lambda r: (-r.score, r.university_id))
    top: list[Recommendation] = []
    for tier in ("dream", "target", "safety"):
        top += [r for r in ranked if r.tier == tier][:1]
    top += [r for r in ranked if r not in top]
    return [by_id[r.university_id] for r in top[: config.TOP_RECS_FOR_ROADMAP] if r.university_id in by_id]


def target_ids(favorite_ids: list[str], recs: list[Recommendation], universities: list[University]) -> list[str]:
    return [u.id for u in _targets(favorite_ids, recs, {u.id: u for u in universities})]


def _names(ids: list[str], by_id: dict[str, University]) -> str:
    names = [by_id[i].name if i in by_id else i for i in ids]
    return ", ".join(names[:3]) + (f" и ещё {len(names) - 3}" if len(names) > 3 else "")


def suggest_actions(profile: Profile, favorite_ids: list[str], recs: list[Recommendation],
                    universities: list[University], added_keys: set[str], today: date,
                    major_names: dict[str, str] | None = None) -> list[Suggestion]:
    by_id = {u.id: u for u in universities}
    major_names = major_names or {}
    out: dict[str, Suggestion] = {}

    def add(key: str, kind: str, title: str, due: date, uni_id: str, source_url: str | None, is_demo: bool) -> None:
        if key in out:  # shared suggestion: keep the earliest due date, merge universities
            s = out[key]
            if due < s.suggested_due:
                s.suggested_due, s.source_url, s.is_demo = due, source_url, is_demo
            if uni_id not in s.university_ids:
                s.university_ids.append(uni_id)
            return
        out[key] = Suggestion(id=key, kind=kind, title=title, why=SuggestionWhy(text="", profile_field=""),
                              description="", suggested_due=due, university_ids=[uni_id], source_url=source_url,
                              is_demo=is_demo, priority=PRIORITY[kind])

    have = {"SAT": best_score(profile, "SAT"), "IELTS": best_ielts(profile)}
    gpa4 = profile_gpa4(profile)
    exam_goals: dict[str, float] = {}
    deadlines: list[date] = []

    # 1. What the target universities require
    for uni in _targets(favorite_ids, recs, by_id):
        dl = application_deadline(uni, profile.intake_year, today)
        if dl is None:
            continue
        deadline, d, dl_demo, dl_source = dl
        deadlines.append(deadline)

        for exam, need in (("SAT", uni.sat.value.p25 if uni.sat.value else None), ("IELTS", uni.ielts_min.value)):
            if need is None or (have[exam] is not None and have[exam] >= need):
                continue
            info = exams()[exam]
            exam_due = deadline - timedelta(days=info["result_days"] + EXAM_BUFFER_DAYS)
            demo = info["is_demo"] or dl_demo
            add(f"exam:{exam}:register", "exam", f"Зарегистрироваться на {info['name']}",
                exam_due - timedelta(days=info["registration_days"]), uni.id, info["source_url"], demo)
            add(f"exam:{exam}", "exam", f"{'Пересдать' if have[exam] is not None else 'Сдать'} {info['name']}",
                exam_due, uni.id, info["source_url"], demo)
            exam_goals[exam] = max(exam_goals.get(exam, 0), need)

        for doc in uni.documents:
            if doc in DOCUMENTS:
                title, lead = DOCUMENTS[doc]
                # dated from the deadline, so exactly as reliable as the deadline
                add(f"doc:{doc}", "document", title, deadline - timedelta(days=lead), uni.id, dl_source, dl_demo)

        if uni.gpa_avg.value is not None and gpa4 is not None and gpa4 < uni.gpa_avg.value - config.GPA_WITHIN_MARGIN:
            add("academic:gpa", "academic", "Подтянуть оценки в текущем семестре",
                deadline - timedelta(days=ACADEMIC_LEAD_DAYS), uni.id, dl_source, dl_demo)

        add(f"apply:{uni.id}:{d.type}", "application", f"Подать заявку: {uni.name} ({text.DEADLINE_RU[d.type]})",
            deadline, uni.id, dl_source, dl_demo)

    for s in out.values():
        kind, _, rest = s.id.partition(":")
        unis = _names(s.university_ids, by_id)
        if kind == "exam":
            exam = rest.split(":")[0]
            name = exams()[exam]["name"]
            field = f"achievement:{exam}"
            if rest.endswith(":register"):
                s.why = SuggestionWhy(text=f"Места на удобные даты {name} заканчиваются заранее", profile_field=field)
            else:
                s.title += f" (цель: {exam_goals[exam]:g}+)"
                s.why = SuggestionWhy(
                    text=(f"{name} ещё не сдан — нужен для: {unis}" if have[exam] is None
                          else f"{name} {have[exam]:g} ниже требований: {unis}"), profile_field=field)
        elif kind == "doc":
            s.why = SuggestionWhy(text=f"Требуется для заявки: {unis}", profile_field="favorites")
        elif kind == "academic":
            s.why = SuggestionWhy(text=f"Средний балл ниже, чем у поступивших: {unis}", profile_field="gpa5")
        elif kind == "apply":
            s.why = SuggestionWhy(text=f"Срок подачи — {s.suggested_due:%d.%m.%Y}", profile_field="favorites")
        s.description = _template_description(s.id)

    # 2. Activities that fit the student's majors and interests
    strong = {a.type for a in done_achievements(profile) if a.level in ("national", "international")}
    top_letter = None
    if profile.holland is not None:
        values = scores(profile.holland)
        if max(values.values()) > min(values.values()):
            top_letter = max(sorted(values), key=lambda c: values[c])
    labels = questionnaire()["dimensions"]
    latest = min(deadlines) - timedelta(days=ACTIVITY_DEADLINE_MARGIN) if deadlines else None
    ielts = have["IELTS"]

    ranked: list[tuple[float, int, dict, SuggestionWhy]] = []
    for order, a in enumerate(activities()):
        if a["min_grade"] > profile.grade or a["achievement_type"] in strong:
            continue
        if a["id"] == "english_practice" and ielts is not None and ielts >= ENGLISH_PRACTICE_ENOUGH:
            continue
        major = next((m for m in profile.majors if m in a["majors"]), None)
        if major:
            points, why = 2.0, SuggestionWhy(text=f"Подходит к направлению «{major_names.get(major, major)}»",
                                              profile_field="majors")
        elif top_letter and top_letter in a["holland"]:
            points, why = 1.0, SuggestionWhy(text=f"Совпадает с вашими интересами: {labels[top_letter].lower()}",
                                              profile_field="holland")
        elif not a["majors"]:
            points, why = 0.5, SuggestionWhy(text="Усиливает заявку в любой вуз", profile_field="achievements")
        else:
            continue
        if major and top_letter and top_letter in a["holland"]:
            points += 1.0
        ranked.append((points, order, a, why))

    for _, _, a, why in sorted(ranked, key=lambda r: (-r[0], r[1]))[:MAX_ACTIVITY_SUGGESTIONS]:
        due = today + timedelta(days=a["lead_days"])
        if latest is not None:
            due = min(due, latest)
        due = max(due, today + timedelta(days=MIN_ACTIVITY_LEAD_DAYS))
        key = f"act:{a['id']}"
        out[key] = Suggestion(id=key, kind=a["kind"], title=a["title"], why=why, description=a["description"],
                              suggested_due=due, university_ids=[], source_url=None, is_demo=False,
                              priority=PRIORITY[a["kind"]])

    return sorted((s for s in out.values() if s.id not in added_keys),
                  key=lambda s: (s.suggested_due, -s.priority, s.id))


def _template_description(key: str) -> str:
    kind, _, rest = key.partition(":")
    if kind == "exam" and rest.endswith(":register"):
        return "Выберите дату и центр тестирования и оплатите регистрацию — места на удобные даты заканчиваются заранее."
    if kind == "exam":
        return "Сдайте экзамен не позже срока: результат приходит не сразу, и его нужно успеть отправить в вузы."
    if kind == "doc":
        name = DOCUMENTS.get(rest, (rest, 0))[0]
        return f"{name}. Начните заранее: документы часто требуют подписи школы и перевода."
    if kind == "apply":
        return "Заполните анкету на сайте вуза, приложите документы и результаты экзаменов, оплатите сбор или запросите освобождение."
    if kind == "academic":
        return "Средний балл ниже, чем у поступивших: сосредоточьтесь на профильных предметах в этом семестре."
    if kind == "act":
        return next((a["description"] for a in activities() if a["id"] == rest), "")
    return ""


def step_description(step: RoadmapStep) -> str:
    """Template text for a plan step: the suggestion's text if it came from one, otherwise the note."""
    if step.source_key:
        return _template_description(step.source_key) or step.title
    return step.note or step.title


def _lead_days(step: RoadmapStep) -> int:
    """How long after finishing a step its result is ready (exam results take time)."""
    key = step.source_key or ""
    if step.kind == "exam" and key.startswith("exam:") and not key.endswith(":register"):
        return exams().get(key.split(":")[1], {}).get("result_days", 0)
    return 0


def build_roadmap(steps: list[RoadmapStep], today: date) -> Roadmap:
    """The student's plan: their own steps, ordered, with dependencies and conflicts derived from them."""
    steps = [s.model_copy(update={"depends_on": [], "priority": PRIORITY[s.kind]}) for s in steps]
    # an application depends on the exams and documents planned for the same university
    for s in steps:
        if s.kind == "application" and s.university_ids:
            s.depends_on = sorted(o.id for o in steps if o.kind in ("exam", "document")
                                  and set(o.university_ids) & set(s.university_ids))
    ordered = sorted(steps, key=lambda s: (s.due_date, -s.priority, s.id))
    done = sum(s.done for s in ordered)
    nxt = next_step(ordered)
    return Roadmap(steps=ordered, conflicts=detect_conflicts(ordered, today),
                   next_step_id=nxt.id if nxt else None, progress=round(done / len(ordered), 3) if ordered else 0.0)


def detect_conflicts(steps: list[RoadmapStep], today: date) -> list[Conflict]:
    by_id = {s.id: s for s in steps}
    out: dict[str, Conflict] = {}
    for s in steps:
        if s.done:
            continue
        for dep_id in s.depends_on:
            dep = by_id.get(dep_id)
            if dep is None or dep.done or dep_id in out:
                continue
            ready = max(today, dep.due_date) + timedelta(days=_lead_days(dep))
            if ready > s.due_date:
                what = "результат" if _lead_days(dep) else "шаг"
                out[dep_id] = Conflict(step_id=dep_id, message=(
                    f"{what.capitalize()} «{dep.title}» будет готов не раньше {ready:%d.%m.%Y} — "
                    f"позже срока «{s.title}» ({s.due_date:%d.%m.%Y}). Перенесите шаг раньше."))
        if s.id not in out and s.due_date < today:
            out[s.id] = Conflict(step_id=s.id, message=f"Срок прошёл {s.due_date:%d.%m.%Y} — перенесите дату или удалите шаг")
    return sorted(out.values(), key=lambda c: c.step_id)


def next_step(steps: list[RoadmapStep]) -> RoadmapStep | None:
    by_id = {s.id: s for s in steps}
    ready = [s for s in steps if not s.done and all(by_id[d].done for d in s.depends_on if d in by_id)]
    return min(ready, key=lambda s: (s.due_date, -s.priority, s.id)) if ready else None
