"""Human Russian texts for reasons, causes and roadmap steps."""

COUNTRY_RU = {
    "US": "США", "UK": "Великобритания", "DE": "Германия", "NL": "Нидерланды", "KR": "Южная Корея",
    "JP": "Япония", "SG": "Сингапур", "CA": "Канада", "HK": "Гонконг", "CH": "Швейцария",
    "IT": "Италия", "FR": "Франция",
}

AID_RU = {
    "full_need": "полная финпомощь по потребности",
    "partial": "частичная финпомощь",
    "merit_only": "только стипендии за достижения",
    "none": "финпомощи для иностранцев нет",
}

DEADLINE_RU = {"ED": "Early Decision", "EA": "Early Action", "REA": "Restrictive EA", "RD": "Regular Decision",
               "UCAS": "UCAS", "OTHER": "Дедлайн"}

LEVEL_RU = {"school": "школьный", "city": "городской", "national": "республиканский", "international": "международный"}


def money(v: int | float) -> str:
    return "$" + f"{int(round(v)):,}".replace(",", "\u00a0")


def country(code: str) -> str:
    return COUNTRY_RU.get(code, code)


def one_in(rate: float) -> str:
    """Acceptance rate as 'about 1 in N' (we never print percentages)."""
    if rate <= 0:
        return "почти никого"
    n = round(1 / rate)
    return "почти всех" if n <= 1 else f"примерно 1 из {n}"
