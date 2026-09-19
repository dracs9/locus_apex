"""Verify extracted facts against the source text and merge verified data into the seed.

Inputs:
  pipeline/out/pages/<id>/*.json      page texts (crawl.py, cds.py)
  pipeline/out/extracted/<id>.json    LLM extraction (extract.py)
  pipeline/cds_manual.json            hand extraction from official CDS text (same shape)
  pipeline/manual_facts.json          hand extraction from official university pages (same shape)
  pipeline/fx.json                    fixed ECB exchange rates for fees published in other currencies
  pipeline/out/scorecard/<id>.json    College Scorecard API values (scorecard.py), already sourced

A page-extracted field is kept only if its value is well-formed and its evidence quote appears verbatim
(whitespace/case-insensitive) in the text of its source_url. Verified values are stored with is_demo=false and
checked_at = the date the source document was fetched; everything else keeps its current seed value and demo flag.
Sources are applied in order (LLM draft, CDS hand extraction, page hand extraction): a later verified fact replaces
an earlier one for the same field or deadline type.

Cost may be given as parts instead of a value:
  {"parts": [{"kind": "tuition"|"living", "amount": 38000, "currency": "GBP", "evidence": "...", "source_url": "..."}]}
Each quote must be on its page and contain its amount; the USD value is then computed here from fx.json, so the
number can't be invented.

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
MANUAL_PAGES = ROOT / "pipeline" / "manual_facts.json"
FX = ROOT / "pipeline" / "fx.json"
SCORECARD = ROOT / "pipeline" / "out" / "scorecard"
VERIFIED = ROOT / "pipeline" / "out" / "verified"
SEED = ROOT / "supabase" / "seed" / "universities.json"
SIMPLE_FIELDS = ("acceptance_rate", "sat", "gpa_avg", "ielts_min", "cost_per_year_usd", "intl_aid")
AID_VALUES = {"full_need", "partial", "merit_only", "none"}
DEADLINE_TYPES = {"ED", "EA", "REA", "RD", "UCAS", "OTHER"}
MIN_EVIDENCE_CHARS = 5


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def valid_value(field: str, v) -> bool:
    """Shape and range check, so a malformed LLM value (85 instead of 0.85, "Nov 1") never reaches the seed."""
    if field == "acceptance_rate":
        return _num(v) and 0 < v <= 1
    if field == "gpa_avg":
        return _num(v) and 0 < v <= 4.5
    if field == "ielts_min":
        return _num(v) and 4 <= v <= 9
    if field == "cost_per_year_usd":
        return _num(v) and v > 0 and float(v).is_integer()
    if field == "intl_aid":
        return v in AID_VALUES
    if field == "sat":
        if not isinstance(v, dict) or not all(_num(v.get(k)) for k in ("p25", "p75")):
            return False
        p50 = v.get("p50")
        return 400 <= v["p25"] <= v["p75"] <= 1600 and (p50 is None or (_num(p50) and v["p25"] <= p50 <= v["p75"]))
    if field == "deadline":
        if not isinstance(v, dict) or v.get("type") not in DEADLINE_TYPES or not isinstance(v.get("date"), str):
            return False
        try:
            date.fromisoformat(v["date"])
        except ValueError:
            return False
        return True
    return False


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip().lower()


def pages(uni_id: str) -> dict[str, dict]:
    """{url: {"text": normalized text, "checked_at": fetch date}} for every stored document of a university."""
    out = {}
    for p in (PAGES / uni_id).glob("*.json"):
        page = json.loads(p.read_text(encoding="utf-8"))
        out[page["url"]] = {"text": normalize(page["text"]), "checked_at": page["fetched_at"][:10]}
    return out


def is_verified(item, docs: dict[str, dict], field: str) -> bool:
    if not isinstance(item, dict) or not valid_value(field, item.get("value")):
        return False
    evidence, url = item.get("evidence"), item.get("source_url")
    if not isinstance(evidence, str) or len(normalize(evidence)) < MIN_EVIDENCE_CHARS or url not in docs:
        return False
    if field == "deadline" and url.startswith("http") and not url.lower().endswith((".pdf", ".xlsx")) \
            and item["value"]["date"][:4] not in evidence:
        return False  # a page deadline must state its year; CDS dates (m/d of the CDS year) are exempt
    return normalize(evidence) in docs[url]["text"]


def amount_in_quote(amount, quote: str) -> bool:
    """The amount must be written in the quote itself: 38000 matches "£38,000", "38 000 €", "EUR 38.000"."""
    if not _num(amount) or amount <= 0 or not float(amount).is_integer():
        return False
    digits = re.sub(r"(?<=\d)[,.\s  '’](?=\d{3}(?!\d))", "", quote)
    digits = re.sub(r"(?<=\d)[.,]00(?!\d)", "", digits)  # zero cents: £9,535.00
    return re.search(rf"(?<![\d.,]){int(amount)}(?!\d|[.,]\d)", digits) is not None


def load_fx() -> dict:
    fx = json.loads(FX.read_text(encoding="utf-8")) if FX.exists() else {"date": None, "usd_per": {}}
    fx["usd_per"] = {"USD": 1.0, **fx["usd_per"]}
    return fx


def cost_from_parts(item, docs: dict[str, dict], fx: dict) -> dict | None:
    """Verified cost {value, evidence, source_url, checked_at} computed from quoted parts, or None."""
    parts = item.get("parts") if isinstance(item, dict) else None
    if not isinstance(parts, list) or not any(isinstance(p, dict) and p.get("kind") == "tuition" for p in parts):
        return None
    total, quotes = 0.0, []
    for part in parts:
        if not isinstance(part, dict) or part.get("kind") not in ("tuition", "living"):
            return None
        rate = fx["usd_per"].get(part.get("currency"))
        quote = {"value": 1, "evidence": part.get("evidence"), "source_url": part.get("source_url")}
        if rate is None or not is_verified(quote, docs, "cost_per_year_usd") \
                or not amount_in_quote(part.get("amount"), part["evidence"]):
            return None
        total += part["amount"] * rate
        label = "Обучение" if part["kind"] == "tuition" else "Проживание"
        quotes.append(f"{label}: «{part['evidence'].strip()}»")
    currencies = sorted({p["currency"] for p in parts} - {"USD"})
    if currencies:
        rates = ", ".join(f"1 {c} = {fx['usd_per'][c]:g} USD" for c in currencies)
        quotes.append(f"курс ЕЦБ на {fx['date']}: {rates}")
    tuition = next(p for p in parts if p["kind"] == "tuition")
    return {"value": int(round(total, -2)), "evidence": " · ".join(quotes), "source_url": tuition["source_url"],
            "checked_at": docs[tuition["source_url"]]["checked_at"]}


def extractions() -> dict[str, list[dict]]:
    """All extraction inputs per university, in order of trust (LLM output, then hand extraction)."""
    out: dict[str, list[dict]] = {}
    if EXTRACTED.exists():
        for path in sorted(EXTRACTED.glob("*.json")):
            out.setdefault(path.stem, []).append(json.loads(path.read_text(encoding="utf-8")))
    for manual in (MANUAL, MANUAL_PAGES):
        if manual.exists():
            for uni_id, data in json.loads(manual.read_text(encoding="utf-8")).items():
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
    fx = load_fx()
    for uni_id, sources in sorted(extractions().items()):
        docs = pages(uni_id)
        kept: dict = {"deadlines": []}
        extracted = verified = 0
        for data in sources:
            if not isinstance(data, dict):
                continue
            for field in SIMPLE_FIELDS:
                item = data.get(field)
                if field == "cost_per_year_usd" and isinstance(item, dict) and "parts" in item:
                    if not item["parts"]:
                        continue
                    extracted += 1
                    cost = cost_from_parts(item, docs, fx)
                    if cost:
                        kept[field] = cost
                        verified += 1
                    else:
                        print(f"  ✗ {uni_id}.cost parts: a quote is not on its page, lacks its amount or has no fx rate")
                    continue
                value = item.get("value") if isinstance(item, dict) else item
                if value is None:
                    continue
                extracted += 1
                if is_verified(item, docs, field):
                    kept[field] = {**item, "checked_at": docs[item["source_url"]]["checked_at"]}
                    verified += 1
                else:
                    print(f"  ✗ {uni_id}.{field}={value!r}: {reject_reason(item, field)}")
            deadlines = data.get("deadlines")
            source_deadlines = []
            for d in deadlines if isinstance(deadlines, list) else []:
                value = d.get("value") if isinstance(d, dict) else d
                if not value:
                    continue
                extracted += 1
                if is_verified(d, docs, "deadline"):
                    source_deadlines.append({**d, "checked_at": docs[d["source_url"]]["checked_at"]})
                    verified += 1
                else:
                    print(f"  ✗ {uni_id}.deadline {value!r}: {reject_reason(d, 'deadline')}")
            types = {d["value"]["type"] for d in source_deadlines}
            kept["deadlines"] = [d for d in kept["deadlines"] if d["value"]["type"] not in types] + source_deadlines

        (VERIFIED / f"{uni_id}.json").write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        verified_all[uni_id] = kept
        report["universities"] += 1
        report["pages"] += len(docs)
        report["fields_extracted"] += extracted
        report["fields_verified"] += verified
        report["by_university"][uni_id] = {"pages": len(docs), "extracted": extracted, "verified": verified}

    total = report["fields_extracted"]
    report["verified_share"] = round(report["fields_verified"] / total, 3) if total else 0.0
    print(f"page extraction: {report['universities']} universities, {report['pages']} documents, "
          f"fields verified {report['fields_verified']}/{total} ({report['verified_share']:.0%})")

    if args.merge:
        report["seed"] = merge(verified_all)
    (ROOT / "pipeline" / "out" / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def reject_reason(item, field: str) -> str:
    if not isinstance(item, dict):
        return "not a {value, evidence, source_url} object"
    if not valid_value(field, item.get("value")):
        return "invalid value"
    return f"evidence not found in {item.get('source_url')}"


def sourced(item: dict) -> dict:
    return {"value": item["value"], "source_url": item["source_url"], "checked_at": item["checked_at"],
            "evidence": re.sub(r"\s+", " ", item["evidence"]).strip(), "is_demo": False}


def merge(verified_all: dict[str, dict]) -> dict:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
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
                uni[field] = sourced(kept[field])
        # 3) deadlines: replace by type, keep unverified types as they are (demo)
        for d in kept.get("deadlines", []):
            uni["deadlines"] = [x for x in uni["deadlines"] if not x["value"] or x["value"]["type"] != d["value"]["type"]]
            uni["deadlines"].append(sourced(d))
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
