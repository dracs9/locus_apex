"""Verify extracted facts against the source text and merge verified data into the seed.

Inputs:
  pipeline/out/pages/<id>/*.json      page texts (crawl.py, cds.py)
  pipeline/out/extracted/<id>.json    LLM extraction (extract.py)
  pipeline/cds_manual.json            hand extraction from official CDS text (same shape)
  pipeline/out/scorecard/<id>.json    College Scorecard API values (scorecard.py), already sourced

A page-extracted field is kept only if its evidence quote appears verbatim (whitespace/case-insensitive)
in the text of its source_url. Verified values are stored with is_demo=false; everything else keeps its
current seed value and demo flag.

Usage:  python pipeline/verify.py [--merge]
Output: pipeline/out/verified/<id>.json, pipeline/out/report.json; with --merge also supabase/seed/universities.json
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pipeline" / "out" / "pages"
EXTRACTED = ROOT / "pipeline" / "out" / "extracted"
MANUAL = ROOT / "pipeline" / "cds_manual.json"
SCORECARD = ROOT / "pipeline" / "out" / "scorecard"
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


def extractions() -> dict[str, list[dict]]:
    """All extraction inputs per university (LLM output and hand extraction)."""
    out: dict[str, list[dict]] = {}
    if EXTRACTED.exists():
        for path in sorted(EXTRACTED.glob("*.json")):
            out.setdefault(path.stem, []).append(json.loads(path.read_text(encoding="utf-8")))
    if MANUAL.exists():
        for uni_id, data in json.loads(MANUAL.read_text(encoding="utf-8")).items():
            if not uni_id.startswith("_"):
                out.setdefault(uni_id, []).append(data)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()
    VERIFIED.mkdir(parents=True, exist_ok=True)

    report = {"universities": 0, "pages": 0, "fields_extracted": 0, "fields_verified": 0, "by_university": {}}
    verified_all: dict[str, dict] = {}
    for uni_id, sources in sorted(extractions().items()):
        texts = page_texts(uni_id)
        kept: dict = {"deadlines": []}
        extracted = verified = 0
        for data in sources:
            for field in SIMPLE_FIELDS:
                item = data.get(field)
                if item and item.get("value") is not None:
                    extracted += 1
                    if is_verified(item, texts):
                        kept[field] = item
                        verified += 1
                    else:
                        print(f"  ✗ {uni_id}.{field}: evidence not found in {item.get('source_url')}")
            for d in data.get("deadlines") or []:
                if not isinstance(d, dict) or not d.get("value"):
                    continue
                extracted += 1
                if is_verified(d, texts):
                    kept["deadlines"].append(d)
                    verified += 1
                else:
                    print(f"  ✗ {uni_id}.deadline {d['value']}: evidence not found")

        (VERIFIED / f"{uni_id}.json").write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        verified_all[uni_id] = kept
        report["universities"] += 1
        report["pages"] += len(texts)
        report["fields_extracted"] += extracted
        report["fields_verified"] += verified
        report["by_university"][uni_id] = {"pages": len(texts), "extracted": extracted, "verified": verified}

    total = report["fields_extracted"]
    report["verified_share"] = round(report["fields_verified"] / total, 3) if total else 0.0
    print(f"page extraction: {report['universities']} universities, {report['pages']} documents, "
          f"fields verified {report['fields_verified']}/{total} ({report['verified_share']:.0%})")

    if args.merge:
        report["seed"] = merge(verified_all)
    (ROOT / "pipeline" / "out" / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def sourced(item: dict, checked_at: str) -> dict:
    return {"value": item["value"], "source_url": item["source_url"], "checked_at": checked_at,
            "evidence": re.sub(r"\s+", " ", item["evidence"]).strip(), "is_demo": False}


def merge(verified_all: dict[str, dict]) -> dict:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    for uni in seed:
        # 1) College Scorecard values (rate, SAT, cost) — already in Sourced form
        card = SCORECARD / f"{uni['id']}.json"
        from_card = json.loads(card.read_text(encoding="utf-8")) if card.exists() else {}
        for field, item in from_card.items():
            uni[field] = item
        # 2) verified page/CDS facts; Scorecard wins for the fields it provides
        kept = verified_all.get(uni["id"], {})
        for field in SIMPLE_FIELDS:
            if field in kept and field not in from_card:
                uni[field] = sourced(kept[field], today)
        # 3) deadlines: replace by type, keep unverified types as they are (demo)
        for d in kept.get("deadlines", []):
            uni["deadlines"] = [x for x in uni["deadlines"] if not x["value"] or x["value"]["type"] != d["value"]["type"]]
            uni["deadlines"].append(sourced(d, today))
        uni["deadlines"].sort(key=lambda x: x["value"]["date"] if x["value"] else "")
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stats = {"universities_with_real_data": 0, "facts_real": 0, "facts_demo": 0}
    for uni in seed:
        facts = [uni[f] for f in SIMPLE_FIELDS] + uni["deadlines"]
        real = sum(not f["is_demo"] for f in facts)
        stats["facts_real"] += real
        stats["facts_demo"] += len(facts) - real
        stats["universities_with_real_data"] += real > 0
    print(f"merged into seed: {stats['facts_real']} real facts, {stats['facts_demo']} demo facts, "
          f"{stats['universities_with_real_data']} universities with real data")
    return stats


if __name__ == "__main__":
    main()
