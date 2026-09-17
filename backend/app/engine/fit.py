"""Fit factors (§8.3): SAT, GPA, IELTS. Each returns a status, a gap and reasons."""
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.schemas import Profile, Reason, University

from . import config
from .normalize import best_ielts, best_score, final_deadline, profile_gpa4, planned_exam_before

AcademicFit = Literal["above", "within", "below", "missing", "skipped"]
LanguageFit = Literal["ok", "missing", "below", "below_planned", "skipped"]


@dataclass
class Fits:
    sat: AcademicFit
    gpa: AcademicFit
    ielts: LanguageFit
    sat_gap: float | None = None
    gpa_gap: float | None = None
    ielts_gap: float | None = None
    reasons: list[Reason] = field(default_factory=list)

    def academic(self) -> list[str]:
        return [f for f in (self.sat, self.gpa) if f != "skipped"]


def _not_published(what: str, field_: str) -> Reason:
    return Reason(kind="risk", code="DATA_NOT_PUBLISHED",
                  text=f"{what}: вуз не публикует данные — оцениваем без этого фактора", profile_field=field_)


def sat_fit(profile: Profile, uni: University) -> tuple[AcademicFit, float | None, list[Reason]]:
    rng = uni.sat.value
    f = "achievement:SAT"
    if rng is None:
        # SAT is a US admission factor; elsewhere its absence is normal and not worth a reason.
        return "skipped", None, ([_not_published("SAT", f)] if uni.country == "US" else [])
    sat = best_score(profile, "SAT")
    if sat is None:
        return "missing", None, [Reason(kind="risk", code="SAT_MISSING",
                                        text=f"SAT ещё не сдан — у поступивших обычно {rng.p25}–{rng.p75}",
                                        profile_field=f)]
    if sat >= rng.p75:
        return "above", None, [Reason(kind="plus", code="SAT_ABOVE_P75",
                                      text=f"Ваш SAT {int(sat)} выше, чем у 75% поступивших ({rng.p75})",
                                      profile_field=f)]
    if sat >= rng.p25:
        return "within", None, [Reason(kind="plus", code="SAT_WITHIN",
                                       text=f"Ваш SAT {int(sat)} в типичном диапазоне {rng.p25}–{rng.p75}",
                                       profile_field=f)]
    gap = float(rng.p25 - sat)
    return "below", gap, [Reason(kind="risk", code="SAT_BELOW_P25",
                                 text=f"SAT {int(sat)} ниже типичного диапазона: нужно ещё +{int(gap)} до {rng.p25}",
                                 profile_field=f, gap=gap)]


def gpa_fit(profile: Profile, uni: University) -> tuple[AcademicFit, float | None, list[Reason]]:
    avg = uni.gpa_avg.value
    if avg is None:
        return "skipped", None, ([_not_published("Средний GPA", "gpa5")] if uni.country == "US" else [])
    gpa4 = profile_gpa4(profile)
    if gpa4 is None:
        return "missing", None, [Reason(kind="risk", code="GPA_NOT_COMPARABLE",
            text="Оценка сохранена в исходной шкале; для сравнения GPA нужен подтверждённый перевод",
            profile_field="gpa5")]
    if gpa4 >= avg:
        return "above", None, [Reason(kind="plus", code="GPA_ABOVE_AVG",
                                      text=f"Ваш GPA ≈{gpa4:.1f} не ниже среднего у поступивших ({avg:.2f})",
                                      profile_field="gpa5")]
    if gpa4 >= avg - config.GPA_WITHIN_MARGIN:
        return "within", None, [Reason(kind="plus", code="GPA_NEAR_AVG",
                                       text=f"Ваш GPA ≈{gpa4:.1f} близок к среднему у поступивших ({avg:.2f})",
                                       profile_field="gpa5")]
    gap = round(avg - gpa4, 2)
    return "below", gap, [Reason(kind="risk", code="GPA_BELOW_AVG",
                                 text=f"GPA ≈{gpa4:.1f} ниже среднего у поступивших ({avg:.2f})",
                                 profile_field="gpa5", gap=gap)]


def ielts_fit(profile: Profile, uni: University) -> tuple[LanguageFit, float | None, list[Reason]]:
    need = uni.ielts_min.value
    f = "achievement:IELTS"
    if need is None:
        return "skipped", None, [_not_published("Минимальный IELTS", f)]
    have = best_ielts(profile)
    if have is None:
        return "missing", None, [Reason(kind="risk", code="IELTS_MISSING",
                                        text=f"Нет сертификата IELTS/TOEFL — нужен IELTS от {need:g}",
                                        profile_field=f)]
    if have >= need:
        return "ok", None, [Reason(kind="plus", code="IELTS_OK",
                                   text=f"Английский ({have:g} по шкале IELTS) проходит минимум {need:g}",
                                   profile_field=f)]
    gap = round(need - have, 1)
    deadline = final_deadline(uni, profile.intake_year)
    planned = planned_exam_before(profile, ("IELTS", "TOEFL"), deadline) if deadline else None
    if planned is not None:
        return "below_planned", gap, [Reason(
            kind="risk", code="IELTS_BELOW_PLANNED",
            text=f"IELTS {have:g} ниже минимума {need:g}, но пересдача запланирована на {planned.date:%d.%m.%Y}",
            profile_field=f, gap=gap)]
    return "below", gap, [Reason(kind="blocker", code="IELTS_BELOW_MIN",
                                 text=f"IELTS {have:g} ниже обязательного минимума {need:g}, пересдача не запланирована",
                                 profile_field=f, gap=gap)]


def compute_fits(profile: Profile, uni: University) -> Fits:
    sat, sat_gap, r1 = sat_fit(profile, uni)
    gpa, gpa_gap, r2 = gpa_fit(profile, uni)
    ielts, ielts_gap, r3 = ielts_fit(profile, uni)
    return Fits(sat=sat, gpa=gpa, ielts=ielts, sat_gap=sat_gap, gpa_gap=gpa_gap, ielts_gap=ielts_gap,
                reasons=r1 + r2 + r3)


def gaps_closable(fits: Fits, uni: University, profile: Profile, today: date) -> bool:
    """A 'below' fit is closable if the gap is small and there is time before the last deadline."""
    deadline = final_deadline(uni, profile.intake_year)
    if deadline is None or (deadline - today).days < config.MIN_DAYS_TO_CLOSE_GAP:
        return False
    if fits.sat == "below" and (fits.sat_gap or 0) > config.SAT_CLOSABLE_GAP:
        return False
    if fits.gpa == "below" and (fits.gpa_gap or 0) > config.GPA4_CLOSABLE_GAP:
        return False
    return True
