"""LLM extraction of admission facts from crawled pages. Every field must carry a verbatim evidence quote.

Usage:  LLM_API_KEY=... python pipeline/extract.py [--ids mit,oxford]
Output: pipeline/out/extracted/<university_id>.json
"""
import argparse
import json
import os
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pipeline" / "out" / "pages"
OUT = ROOT / "pipeline" / "out" / "extracted"
MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
MAX_CHARS_PER_PAGE = 12000

FIELDS = {
    "acceptance_rate": "overall acceptance rate as a number 0..1",
    "sat": "object {p25, p75} of SAT total scores of enrolled/admitted students",
    "gpa_avg": "average high-school GPA on a 4.0 scale",
    "ielts_min": "minimum overall IELTS score for undergraduate admission",
    "cost_per_year_usd": "tuition + living cost per year for international undergraduates in USD (convert only if the page gives a USD figure, otherwise null)",
    "intl_aid": "one of full_need | partial | merit_only | none — financial aid for international undergraduates",
    "deadlines": "LIST of items, each {value: {type: ED|EA|REA|RD|UCAS|OTHER, date: YYYY-MM-DD}, evidence, source_url} — first-year undergraduate application deadlines",
}

SYSTEM = (
    "You extract university admission facts from web pages. Use ONLY the given pages. "
    "For every field return {value, evidence, source_url}: evidence is an exact verbatim quote (max 300 chars) copied from the page text that states the value; "
    "source_url is the url of that page. If a fact is not stated, return {value: null, evidence: null, source_url: null}. "
    "Never guess or use outside knowledge. Return JSON with exactly these keys: " + json.dumps(FIELDS)
)


def extract(client: genai.Client, uni_id: str) -> dict | None:
    pages = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((PAGES / uni_id).glob("*.json"))]
    if not pages:
        return None
    payload = [{"url": p["url"], "text": p["text"][:MAX_CHARS_PER_PAGE]} for p in pages]
    res = client.models.generate_content(
        model=MODEL,
        contents=json.dumps({"university_id": uni_id, "pages": payload}, ensure_ascii=False),
        config=types.GenerateContentConfig(system_instruction=SYSTEM, response_mime_type="application/json", temperature=0),
    )
    try:
        return json.loads(res.text or "")
    except json.JSONDecodeError:
        print(f"{uni_id}: invalid JSON from model, skipped")
        return None


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
