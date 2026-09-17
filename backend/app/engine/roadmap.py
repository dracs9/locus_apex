"""Roadmap (§8.7): steps with deterministic ids, due dates computed backwards from deadlines."""
import json
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from app.schemas import Conflict, Profile, Recommendation, Roadmap, RoadmapStep, University

from . import config, text
from .normalize import application_deadline, best_ielts, best_score, done_achievements, gpa5_to_gpa4

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
ACTIVITY_LEAD_DAYS = 120
ACADEMIC_LEAD_DAYS = 90


@cache
def exams() -> dict:
    return json.loads((Path(__file__).parent.parent / "data" / "exams.json").read_text(encoding="utf-8"))


def _lead_days(step: RoadmapStep) -> int:
    """How long after starting a step its result is ready."""
    if step.kind == "exam" and not step.id.endswith(":register"):
        return exams()[step.id.split(":")[1]]["result_days"]
    return 0


def _targets(favorite_ids: list[str], recs: list[Recommendation], by_id: dict[str, University]) -> list[University]:
    favs = [by_id[i] for i in sorted(set(favorite_ids)) if i in by_id]
    if favs:
        return favs
    top = sorted(recs, key=lambda r: (-r.score, r.university_id))[: config.TOP_RECS_FOR_ROADMAP]
    return [by_id[r.university_id] for r in top if r.university_id in by_id]


def build_roadmap(profile: Profile, favorite_ids: list[str], recs: list[Recommendation],
                  universities: list[University], progress: dict[str, bool], today: date) -> Roadmap:
    by_id = {u.id: u for u in universities}
    steps: dict[str, RoadmapStep] = {}

    def add(step_id: str, kind: str, title: str, due: date, uni_id: str, depends_on: list[str] | None = None,
            source_url: str | None = None, is_demo: bool = True) -> None:
        if step_id in steps:  # shared step: keep the earliest due date, merge universities
            s = steps[step_id]
            if due < s.due_date:
                s.due_date, s.source_url, s.is_demo = due, source_url, is_demo
            if uni_id not in s.university_ids:
                s.university_ids.append(uni_id)
            for d in depends_on or []:
                if d not in s.depends_on:
                    s.depends_on.append(d)
            return
        steps[step_id] = RoadmapStep(id=step_id, kind=kind, title=title, due_date=due, depends_on=list(depends_on or []),
                                     university_ids=[uni_id], source_url=source_url, is_demo=is_demo,
                                     done=progress.get(step_id, False), priority=PRIORITY[kind])

    sat = best_score(profile, "SAT")
    ielts = best_ielts(profile)
    gpa4 = gpa5_to_gpa4(profile.gpa5)
    exam_goals: dict[str, float] = {}
    strong_activity = any(a.type in config.ACTIVITY_TYPES and a.level in ("national", "international")
                          for a in done_achievements(profile))

    for uni in _targets(favorite_ids, recs, by_id):
        dl = application_deadline(uni, profile.intake_year, today)
        if dl is None:
            continue
        deadline, d, dl_demo, dl_source = dl
        apply_id = f"apply:{uni.id}:{d.type}"
        apply_deps: list[str] = []

        for exam, need, have in (("SAT", uni.sat.value.p25 if uni.sat.value else None, sat),
                                 ("IELTS", uni.ielts_min.value, ielts)):
            if need is None or (have is not None and have >= need):
                continue
            info = exams()[exam]
            exam_id = f"exam:{exam}"
            exam_due = deadline - timedelta(days=info["result_days"] + EXAM_BUFFER_DAYS)
            verb = "Пересдать" if have is not None else "Сдать"
            add(f"{exam_id}:register", "exam", f"Зарегистрироваться на {info['name']}",
                exam_due - timedelta(days=info["registration_days"]), uni.id,
                source_url=info["source_url"], is_demo=info["is_demo"])
            exam_goals[exam] = max(exam_goals.get(exam, 0), need)
            add(exam_id, "exam", f"{verb} {info['name']}", exam_due, uni.id,
                depends_on=[f"{exam_id}:register"], source_url=info["source_url"], is_demo=info["is_demo"])
            apply_deps.append(exam_id)

        for doc in uni.documents:
            if doc not in DOCUMENTS:
                continue
            title, lead = DOCUMENTS[doc]
            add(f"doc:{doc}", "document", title, deadline - timedelta(days=lead), uni.id)
            apply_deps.append(f"doc:{doc}")

        if uni.gpa_avg.value is not None and gpa4 < uni.gpa_avg.value - config.GPA_WITHIN_MARGIN:
            add("academic:gpa", "academic", "Подтянуть оценки в текущем семестре", deadline - timedelta(days=ACADEMIC_LEAD_DAYS), uni.id)
        if not strong_activity:
            add("activity:highlight", "activity", "Олимпиада или проект республиканского уровня",
                deadline - timedelta(days=ACTIVITY_LEAD_DAYS), uni.id)

        add(apply_id, "application", f"Подать заявку: {uni.name} ({text.DEADLINE_RU[d.type]})", deadline, uni.id,
            depends_on=apply_deps, source_url=dl_source, is_demo=dl_demo)

    for exam, goal in exam_goals.items():  # the goal must satisfy the strictest university
        steps[f"exam:{exam}"].title += f" (цель: {goal:g}+)"

    ordered = sorted(steps.values(), key=lambda s: (s.due_date, -s.priority, s.id))
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
            ready = today + timedelta(days=_lead_days(dep))
            if ready > s.due_date:
                what = "результат" if _lead_days(dep) else "шаг"
                out[dep_id] = Conflict(step_id=dep_id, message=(
                    f"Даже если начать сегодня, {what} «{dep.title}» будет готов к {ready:%d.%m.%Y} — "
                    f"позже срока «{s.title}» ({s.due_date:%d.%m.%Y})"))
        if s.id not in out and s.due_date < today:
            out[s.id] = Conflict(step_id=s.id, message=f"Срок прошёл {s.due_date:%d.%m.%Y} — выберите другой дедлайн или вуз")
    return sorted(out.values(), key=lambda c: c.step_id)


def next_step(steps: list[RoadmapStep]) -> RoadmapStep | None:
    by_id = {s.id: s for s in steps}
    ready = [s for s in steps if not s.done and all(by_id[d].done for d in s.depends_on if d in by_id)]
    return min(ready, key=lambda s: (s.due_date, -s.priority, s.id)) if ready else None
