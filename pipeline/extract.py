"""LLM extraction of admission facts from crawled pages. Every field must carry a verbatim evidence quote.

Usage:  LLM_API_KEY=... python pipeline/extract.py [--ids mit,oxford]
Output: pipeline/out/extracted/<university_id>.json
"""
import argparse
import json
import os
import re
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pipeline" / "out" / "pages"
OUT = ROOT / "pipeline" / "out" / "extracted"
MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
MAX_CHARS_PER_PAGE = 30000

FIELDS = {
    "acceptance_rate": "overall acceptance rate as a number 0..1",
    "sat": "object {p25, p75} of SAT total scores of enrolled/admitted students",
    "gpa_avg": "average high-school GPA on a 4.0 scale",
    "ielts_min": "minimum overall IELTS score for undergraduate admission",
    "cost_per_year_usd": "NOT a value: {parts: [{kind: tuition|living, amount: integer per ONE academic year in the "
                         "page's currency, currency: ISO code (GBP, EUR, ...), evidence, source_url}]} — annual tuition "
                         "for NON-EU / international BACHELOR students (a typical or the listed programme) and, if the "
                         "university states it, its estimate of yearly living costs. If only a monthly living cost is "
                         "given, omit living. If no annual international undergraduate tuition is stated, return {parts: []}",
    "intl_aid": "one of full_need | partial | merit_only | none — financial aid for international undergraduates: "
                "full_need = meets full demonstrated need; partial = need-based aid that doesn't cover full need or "
                "tuition waivers/scholarships covering a large share; merit_only = only merit scholarships; "
                "none = states that no aid is available to international students",
    "deadlines": "LIST of items, each {value: {type: ED|EA|REA|RD|UCAS|OTHER, date: YYYY-MM-DD}, evidence, source_url} "
                 "— first-year undergraduate application deadlines for INTERNATIONAL applicants for the NEXT intake "
                 "(the latest year stated; skip past cycles). At most one item per type: the general deadline, not one "
                 "for a single subject such as medicine. The date must be written with its year in the quote",
}

SYSTEM = (
    "You extract university admission facts from web pages. Use ONLY the given pages. "
    "For every field return {value, evidence, source_url}: evidence is an exact verbatim quote (max 300 chars) copied from the page text that states the value; "
    "source_url is the url of that page. If a fact is not stated, return {value: null, evidence: null, source_url: null}. "
    "Facts must be about BACHELOR (undergraduate) admission, not master's or PhD. "
    "Never guess or use outside knowledge. Return JSON with exactly these keys: " + json.dumps(FIELDS)
)


MAX_PAGES = 14
RELEVANT = re.compile(r"ielts|tuition|fees?\b|living costs?|cost of living|deadline|closing date|scholarship|"
                      r"financial aid|international (students|applicants)|non-eu|overseas", re.I)
NOISE = re.compile(r"postgraduate|graduate|master|phd|doctoral|/news/|/events?/", re.I)


def relevance(page: dict) -> float:
    """Pages about undergraduate fees / requirements / deadlines first; graduate and news pages last."""
    hits = len(RELEVANT.findall(page["text"][:MAX_CHARS_PER_PAGE])) + 5 * len(RELEVANT.findall(page["url"]))
    return hits - (20 if NOISE.search(page["url"]) else 0)


def extract(client: genai.Client, uni_id: str) -> dict | None:
    pages = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((PAGES / uni_id).glob("*.json"))]
    pages = [p for p in pages if p["text"].strip()]
    if not pages:
        return None
    pages = sorted(pages, key=relevance, reverse=True)[:MAX_PAGES]
    payload = [{"url": p["url"], "text": p["text"][:MAX_CHARS_PER_PAGE]} for p in pages]
    try:
        res = client.models.generate_content(
            model=MODEL,
            contents=json.dumps({"university_id": uni_id, "pages": payload}, ensure_ascii=False),
            config=types.GenerateContentConfig(system_instruction=SYSTEM, response_mime_type="application/json", temperature=0),
        )
    except Exception as e:  # network, quota, safety block: skip this university, keep going
        print(f"{uni_id}: model call failed ({type(e).__name__}: {e}), skipped")
        return None
    try:
        data = json.loads(res.text or "")
    except json.JSONDecodeError:
        print(f"{uni_id}: invalid JSON from model, skipped")
        return None
    if not isinstance(data, dict):
        print(f"{uni_id}: model returned {type(data).__name__}, expected an object, skipped")
        return None
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids")
    args = parser.parse_args()
    client = genai.Client(api_key=os.environ["LLM_API_KEY"])
    OUT.mkdir(parents=True, exist_ok=True)
    ids = args.ids.split(",") if args.ids else sorted(p.name for p in PAGES.iterdir() if p.is_dir())
    for uni_id in ids:
        data = extract(client, uni_id)
        if data is not None:
            (OUT / f"{uni_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{uni_id}: extracted")


if __name__ == "__main__":
    main()
