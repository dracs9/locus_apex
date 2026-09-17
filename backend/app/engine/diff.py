"""Diff between two snapshots (§8.6) and the human 'cause' of a change."""
from app.schemas import ChanceChange, Diff, GapClosed, Profile, Snapshot, TierChange

from . import config, text
from .normalize import best_ielts, best_score


def diff(prev: Snapshot | None, new: Snapshot) -> Diff | None:
    if prev is None:
        return None
    prev_recs = {r.university_id: r for r in prev.result.recs}
    new_recs = {r.university_id: r for r in new.result.recs}
    prev_excluded = {e.university_id: e for e in prev.result.excluded}

    tier_changed, chance_changed, gaps_closed = [], [], []
    for uid in sorted(prev_recs.keys() & new_recs.keys()):
        a, b = prev_recs[uid], new_recs[uid]
        if a.tier != b.tier:
            tier_changed.append(TierChange(id=uid, from_=a.tier, to=b.tier))
        if a.chance != b.chance:
            chance_changed.append(ChanceChange(id=uid, from_=a.chance, to=b.chance))
    for uid in sorted(new_recs):
        before = prev_recs.get(uid) or prev_excluded.get(uid)
        if before is None:
            continue
        after_codes = {r.code for r in new_recs[uid].reasons}
        for code in sorted({r.code for r in before.reasons if r.code in config.GAP_CODES} - after_codes):
            gaps_closed.append(GapClosed(id=uid, code=code))

    return Diff(
        added=sorted(new_recs.keys() - prev_recs.keys()),
        removed=sorted(prev_recs.keys() - new_recs.keys()),
        tier_changed=tier_changed,
        chance_changed=chance_changed,
        gaps_closed=gaps_closed,
        roadmap_added=sorted(set(new.roadmap_step_ids) - set(prev.roadmap_step_ids)),
        roadmap_removed=sorted(set(prev.roadmap_step_ids) - set(new.roadmap_step_ids)),
        cause=new.cause,
    )


def _score_text(v: float | None) -> str:
    return "—" if v is None else f"{v:g}"


def describe_changes(prev: Profile | None, new: Profile, major_names: dict[str, str] | None = None) -> str:
    """Human text of what changed between two profile versions."""
    names = major_names or {}
    if prev is None:
        return "Профиль создан"
    parts: list[str] = []
    if prev.budget_per_year_usd != new.budget_per_year_usd:
        parts.append(f"бюджет {text.money(prev.budget_per_year_usd)} → {text.money(new.budget_per_year_usd)}")
    if prev.needs_aid != new.needs_aid:
        parts.append("нужна финпомощь" if new.needs_aid else "финпомощь не нужна")
    if prev.majors != new.majors:
        parts.append("направления: " + ", ".join(names.get(m, m) for m in new.majors))
    if prev.countries != new.countries:
        parts.append("страны: " + ", ".join(text.country(c) for c in new.countries))
    if prev.gpa5 != new.gpa5 or prev.academic_record != new.academic_record:
        parts.append("обновлена оценка или шкала оценивания")
    if prev.holland != new.holland:
        parts.append("обновлены интересы RIASEC")
    if prev.grade != new.grade:
        parts.append(f"класс {prev.grade} → {new.grade}")
    if prev.intake_year != new.intake_year:
        parts.append(f"год поступления {prev.intake_year} → {new.intake_year}")
    if prev.priorities != new.priorities:
        parts.append("приоритеты")
    for exam in ("SAT", "IELTS"):
        a = best_score(prev, exam) if exam == "SAT" else best_ielts(prev)
        b = best_score(new, exam) if exam == "SAT" else best_ielts(new)
        if a != b:
            parts.append(f"{exam} {_score_text(a)} → {_score_text(b)}")
    prev_ids = {a.id: a for a in prev.achievements}
    new_ids = {a.id: a for a in new.achievements}
    added = [a for i, a in new_ids.items() if i not in prev_ids and a.type not in ("SAT", "IELTS", "TOEFL")]
    removed = [a for i, a in prev_ids.items() if i not in new_ids and a.type not in ("SAT", "IELTS", "TOEFL")]
    if added:
        parts.append("добавлено достижение: " + ", ".join(a.title or a.type for a in added))
    if removed:
        parts.append("удалено достижение: " + ", ".join(a.title or a.type for a in removed))
    if not parts and prev.achievements != new.achievements:
        parts.append("обновлены достижения")
    if not parts:
        return "Маршрут пересчитан"
    s = "; ".join(parts)
    return s[0].upper() + s[1:]
