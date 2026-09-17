"""Template texts used when the LLM is disabled, slow or returns invalid JSON."""
from collections import Counter

from app.engine import text
from app.engine.normalize import best_ielts, best_score, done_achievements, gpa5_to_gpa4
from app.engine.roadmap import DOCUMENTS
from app.schemas import Profile, RecommendationResult, RoadmapStep, University
from app.schemas.ai import PassportItem, PassportOut

LEVEL_RANK = {"international": 4, "national": 3, "city": 2, "school": 1, None: 0}

RISK_SUMMARY = {
    "SAT_BELOW_P25": "SAT ниже типичного диапазона",
    "SAT_MISSING": "SAT ещё не сдан",
    "GPA_BELOW_AVG": "средний балл ниже, чем у поступивших",
    "IELTS_MISSING": "нет сертификата по английскому",
    "IELTS_BELOW_PLANNED": "IELTS ниже минимума (пересдача запланирована)",
    "OVER_BUDGET_NEEDS_AID": "вуз дороже бюджета — всё зависит от финпомощи",
    "VERY_SELECTIVE": "очень высокий конкурс",
    "COST_UNKNOWN": "стоимость не опубликована",
    "AID_UNKNOWN": "условия финпомощи не опубликованы",
}


def passport(profile: Profile, result: RecommendationResult, major_names: dict[str, str]) -> PassportOut:
    majors = ", ".join(major_names.get(m, m) for m in profile.majors)
    countries = ", ".join(text.country(c) for c in profile.countries)
    goal = PassportItem(text=f"Поступить на «{majors}» — {countries}, старт учёбы в {profile.intake_year} году",
                        profile_field="majors")

    strengths: list[PassportItem] = []
    gpa4 = gpa5_to_gpa4(profile.gpa5)
    if profile.gpa5 >= 4.5:
        strengths.append(PassportItem(text=f"Высокий средний балл {profile.gpa5:g} (≈{gpa4:.1f} GPA)", profile_field="gpa5"))
    sat = best_score(profile, "SAT")
    if sat is not None and sat >= 1300:
        strengths.append(PassportItem(text=f"SAT уже сдан: {int(sat)}", profile_field="achievement:SAT"))
    ielts = best_ielts(profile)
    if ielts is not None and ielts >= 6.5:
        strengths.append(PassportItem(text=f"Английский на уровне IELTS {ielts:g}", profile_field="achievement:IELTS"))
    activities = sorted((a for a in done_achievements(profile) if a.type not in ("SAT", "IELTS", "TOEFL")),
                        key=lambda a: (-LEVEL_RANK[a.level], a.date))
    if activities:
        a = activities[0]
        level = f" ({text.LEVEL_RU[a.level]} уровень)" if a.level else ""
        strengths.append(PassportItem(text=f"{a.title or a.type}{level}", profile_field="achievements"))
    if profile.grade <= 11:
        strengths.append(PassportItem(text=f"Есть время подготовиться: сейчас {profile.grade} класс", profile_field="grade"))
    safe = sum(r.tier == "safety" for r in result.recs)
    if safe:
        strengths.append(PassportItem(text=f"Есть надёжные варианты: {safe}", profile_field="majors"))
    strengths.append(PassportItem(text=f"Понятная цель: {majors}", profile_field="majors"))

    constraints = [PassportItem(text=f"Бюджет до {text.money(profile.budget_per_year_usd)} в год", profile_field="budget_per_year_usd")]
    if profile.needs_aid:
        constraints.append(PassportItem(text="Нужна финансовая помощь — это сужает выбор", profile_field="needs_aid"))
    elif ielts is None:
        constraints.append(PassportItem(text="Пока нет сертификата IELTS/TOEFL", profile_field="achievement:IELTS"))
    elif sat is None:
        constraints.append(PassportItem(text="Пока нет результата SAT (важно для США)", profile_field="achievement:SAT"))
    else:
        constraints.append(PassportItem(text=f"Выбрано стран: {len(profile.countries)}", profile_field="countries"))

    risk_codes = Counter(r.code for rec in result.recs for r in rec.reasons if r.kind == "risk" and r.code in RISK_SUMMARY)
    if risk_codes:
        code, n = sorted(risk_codes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        field = next(r.profile_field for rec in result.recs for r in rec.reasons if r.code == code)
        risk = PassportItem(text=f"Главный риск: {RISK_SUMMARY[code]} (вузов: {n})", profile_field=field)
    elif not result.recs:
        risk = PassportItem(text="Сейчас нет подходящих вузов — посмотрите подсказки, что изменить", profile_field="countries")
    else:
        risk = PassportItem(text="Серьёзных рисков не видно — главное не пропустить дедлайны", profile_field="intake_year")
    return PassportOut(goal=goal, strengths=strengths[:3], constraints=constraints[:2], risk=risk, generated=False)


def explain(uni: University, reasons_texts: list[tuple[str, str]], tier: str | None) -> str:
    """reasons_texts: [(kind, text)]."""
    tier_ru = {"dream": "мечта", "target": "реальный вариант", "safety": "надёжный вариант"}
    pluses = [t for k, t in reasons_texts if k == "plus"]
    risks = [t for k, t in reasons_texts if k in ("risk", "blocker")]
    head = f"{uni.name} — {tier_ru[tier]}" if tier else f"{uni.name} сейчас не подходит"
    first = f"{head}: {_lc(pluses[0]) if pluses else (_lc(risks[0]) if risks else 'данных мало')}."
    if risks and pluses:
        return f"{first} Главное, что стоит учесть: {_lc(risks[0])}."
    return first


def _lc(s: str) -> str:
    """Lowercase the first letter unless the first word is an acronym (SAT, IELTS...)."""
    word = s.split(" ", 1)[0]
    return s if word.isupper() else s[:1].lower() + s[1:]


def step_description(step: RoadmapStep) -> str:
    kind, _, rest = step.id.partition(":")
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
    if kind == "activity":
        return "Одно сильное достижение (олимпиада, проект, конкурс) заметно усиливает заявку в топ-вузы."
    return step.title
