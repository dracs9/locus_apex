"""Fixed exchange rates for converting published fees to USD: ECB euro foreign exchange reference rates.

The rates are fetched once and committed, so the seed doesn't change when the script is re-run on another day.
Usage:  python pipeline/fx.py
Output: pipeline/fx.json  {date, source, usd_per: {currency: USD for 1 unit}}
"""
import json
import re
from pathlib import Path

import httpx

URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
OUT = Path(__file__).resolve().parent / "fx.json"
CURRENCIES = ("EUR", "GBP", "CHF", "SEK", "AUD", "CAD", "SGD", "HKD", "CNY", "JPY", "KRW")


def usd_per(per_eur: dict[str, float]) -> dict[str, float]:
    """ECB quotes units per 1 EUR; USD per 1 unit of X = (USD per EUR) / (X per EUR)."""
    usd = per_eur["USD"]
    return {c: round(usd / (1.0 if c == "EUR" else per_eur[c]), 6) for c in CURRENCIES}


def main() -> None:
    xml = httpx.get(URL, timeout=20).text
    day = re.search(r"time='(\d{4}-\d{2}-\d{2})'", xml).group(1)
    per_eur = {c: float(r) for c, r in re.findall(r"currency='([A-Z]{3})' rate='([\d.]+)'", xml)}
    data = {"date": day, "source": "ECB euro foreign exchange reference rates", "source_url": URL,
            "usd_per": usd_per(per_eur)}
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
