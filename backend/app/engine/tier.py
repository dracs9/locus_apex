"""Tier + chance (§8.5). First matching rule wins. Chance is a label, never a percentage."""
from datetime import date

from app.schemas import Profile, Reason, University
from app.schemas.recommendation import Chance, Tier

from . import config, text
from .fit import Fits, gaps_closable


def tier_and_chance(profile: Profile, uni: University, fits: Fits, today: date) -> tuple[Tier, Chance, list[Reason]]:
    """Returns tier, chance and extra reasons explaining the tier."""
    rate = uni.acceptance_rate.value
    academic = fits.academic()
    all_above = bool(academic) and all(f == "above" for f in academic) and fits.ielts in ("ok", "skipped")

    if rate is not None and rate < config.DREAM_ACCEPTANCE_BELOW:
        return "dream", ("medium" if all_above else "low"), [Reason(
            kind="risk", code="VERY_SELECTIVE",
            text=f"Очень высокий конкурс: принимают {text.one_in(rate)} заявителей (общая статистика)",
            profile_field="majors")]

    if "below" in academic or fits.ielts == "below_planned":
        if gaps_closable(fits, uni, profile, today):
            extra = Reason(kind="risk", code="GAP_CLOSABLE",
                           text="Разрыв можно закрыть до дедлайна — вуз останется мечтой, пока его не закроете",
                           profile_field="achievement:SAT" if fits.sat == "below" else "gpa5")
        else:
            # The spec only names the closable case; an unclosable gap is still a reach, never a target.
            extra = Reason(kind="risk", code="GAP_HARD_TO_CLOSE",
                           text="Разрыв большой или до дедлайна мало времени — это амбициозный выбор",
                           profile_field="achievement:SAT" if fits.sat == "below" else "gpa5")
        return "dream", "low", [extra]

    fits_ok = all(f in ("above", "within") for f in academic) and fits.ielts in ("ok", "skipped")
    if fits_ok and rate is not None and rate >= config.SAFETY_ACCEPTANCE_FROM:
        return "safety", "high", [Reason(
            kind="plus", code="ACCESSIBLE",
            text=f"Ваши показатели в диапазоне поступивших, принимают {text.one_in(rate)} заявителей",
            profile_field="gpa5")]
    return "target", "medium", []
