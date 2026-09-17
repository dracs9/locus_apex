"""Drop every extracted field whose evidence quote is not found in the source page text; write a report.

Usage:  python pipeline/verify.py [--merge]
  --merge  write verified values into supabase/seed/universities.json with source_url, evidence and checked_at.
           is_demo stays true: machine-verified is not human-verified. A reviewer flips is_demo to false.
Output: pipeline/out/verified/<university_id>.json, pipeline/out/report.json
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pipeline" / "out" / "pages"
EXTRACTED = ROOT / "pipeline" / "out" / "extracted"
VERIFIED = ROOT / "pipeline" / "out" / "verified"
SEED = ROOT / "supabase" / "seed" / "universities.json"
SIMPLE_FIELDS = ("acceptance_rate", "sat", "gpa_avg", "ielts_min", "cost_per_year_usd", "intl_aid")


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip().lower()


def page_texts(uni_id: str) -> dict[str, str]:
    out = {}
    for p in (PAGES / uni_id).glob("*.json"):
        page = json.loads(p.read_text(encoding="utf-8"))
        out[page["url"]] = normalize(page["text"])
    return out


def is_verified(item: dict | None, texts: dict[str, str]) -> bool:
    if not item or item.get("value") is None or not item.get("evidence") or not item.get("source_url"):
        return False
    text = texts.get(item["source_url"])
    return text is not None and normalize(item["evidence"]) in text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()
    VERIFIED.mkdir(parents=True, exist_ok=True)

    report = {"universities": 0, "pages": 0, "fields_extracted": 0, "fields_verified": 0, "by_university": {}}
    verified_all: dict[str, dict] = {}
    for path in sorted(EXTRACTED.glob("*.json")):
        uni_id = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        texts = page_texts(uni_id)
        kept: dict = {}
        extracted = verified = 0
        for field in SIMPLE_FIELDS:
            item = data.get(field)
            if item and item.get("value") is not None:
                extracted += 1
                if is_verified(item, texts):
                    kept[field] = item
                    verified += 1
        deadlines = [d for d in (data.get("deadlines") or []) if isinstance(d, dict)]
        good_deadlines = []
        for d in deadlines:
            extracted += 1
            if is_verified(d, texts):
                good_deadlines.append(d)
                verified += 1
        kept["deadlines"] = good_deadlines

        (VERIFIED / f"{uni_id}.json").write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        verified_all[uni_id] = kept
        report["universities"] += 1
        report["pages"] += len(texts)
        report["fields_extracted"] += extracted
        report["fields_verified"] += verified
        report["by_university"][uni_id] = {"pages": len(texts), "extracted": extracted, "verified": verified}

    total = report["fields_extracted"]
    report["verified_share"] = round(report["fields_verified"] / total, 3) if total else 0.0
    (ROOT / "pipeline" / "out" / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"universities: {report['universities']}, pages: {report['pages']}, "
          f"fields verified: {report['fields_verified']}/{total} ({report['verified_share']:.0%})")

    if args.merge:
        merge(verified_all)


def merge(verified_all: dict[str, dict]) -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    for uni in seed:
        kept = verified_all.get(uni["id"])
        if not kept:
            continue
        for field in SIMPLE_FIELDS:
            if field in kept:
                item = kept[field]
                uni[field] = {"value": item["value"], "source_url": item["source_url"], "checked_at": today,
                              "evidence": item["evidence"], "is_demo": True}
        if kept.get("deadlines"):
            uni["deadlines"] = [{"value": {"type": d["value"]["type"], "date": d["value"]["date"]},
                                 "source_url": d["source_url"], "checked_at": today, "evidence": d["evidence"],
                                 "is_demo": True} for d in kept["deadlines"]]
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("merged verified fields into supabase/seed/universities.json (is_demo left true for human review)")


if __name__ == "__main__":
    main()
