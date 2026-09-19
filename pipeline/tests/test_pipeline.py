"""Tests for the pure parts of the pipeline. Run: .venv/Scripts/python -m pytest pipeline/tests -q"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import crawl  # noqa: E402
import verify  # noqa: E402

URL = "https://example.edu/cds.pdf"
DOCS = {URL: {"text": verify.normalize("C12. Average high school GPA: 3.9\nC21 closing date (fall) 1/5"),
              "checked_at": "2026-09-17"}}


@pytest.mark.parametrize("host, root", [
    ("admissions.purdue.edu", "purdue.edu"),
    ("www.ox.ac.uk", "ox.ac.uk"),
    ("www.undergraduate.study.cam.ac.uk", "cam.ac.uk"),
    ("www.nus.edu.sg", "nus.edu.sg"),
    ("admission.kaist.ac.kr", "kaist.ac.kr"),
    ("ethz.ch", "ethz.ch"),
    ("WWW.TUM.DE:443", "tum.de"),
])
def test_site_root(host, root):
    assert crawl.site_root(host) == root


def test_same_site_stays_on_the_university():
    assert crawl.same_site("www.ox.ac.uk", "ox.ac.uk")
    assert crawl.same_site("ox.ac.uk", "ox.ac.uk")
    assert not crawl.same_site("www.cam.ac.uk", "ox.ac.uk")
    assert not crawl.same_site("notmit.edu", "mit.edu")


def fact(value, evidence="Average high school GPA: 3.9", url=URL):
    return {"value": value, "evidence": evidence, "source_url": url}


def test_verified_fact():
    assert verify.is_verified(fact(3.9), DOCS, "gpa_avg")
    assert verify.is_verified(fact({"type": "RD", "date": "2025-01-05"}, "closing date (fall) 1/5"), DOCS, "deadline")


@pytest.mark.parametrize("item", [
    fact(3.9, evidence="   "),                # blank evidence is in every text
    fact(3.9, evidence="3.9"),                # too short to prove anything
    fact(3.9, evidence="GPA: 4.0"),           # not in the document
    fact(3.9, url="https://other.edu/x"),     # unknown document
    {"value": 3.9},                           # no evidence at all
    3.9,                                      # bare value instead of an object
    None,
])
def test_unverified_fact(item):
    assert not verify.is_verified(item, DOCS, "gpa_avg")


@pytest.mark.parametrize("field, value", [
    ("acceptance_rate", 85), ("acceptance_rate", "85%"), ("acceptance_rate", 0),
    ("gpa_avg", 5.0), ("ielts_min", 70), ("cost_per_year_usd", -1), ("cost_per_year_usd", 1.5),
    ("intl_aid", "yes"), ("sat", {"p25": 1500, "p75": 1400}), ("sat", {"p25": 30, "p75": 34}),
    ("deadline", {"type": "Early", "date": "2025-11-01"}), ("deadline", {"type": "EA", "date": "Nov 1"}),
    ("acceptance_rate", True),
])
def test_invalid_values(field, value):
    assert not verify.valid_value(field, value)


@pytest.mark.parametrize("field, value", [
    ("acceptance_rate", 0.05), ("gpa_avg", 3.9), ("ielts_min", 7.0), ("cost_per_year_usd", 90000),
    ("intl_aid", "merit_only"), ("sat", {"p25": 1500, "p50": None, "p75": 1570}),
    ("deadline", {"type": "UCAS", "date": "2026-01-14"}),
])
def test_valid_values(field, value):
    assert verify.valid_value(field, value)


def test_merge_uses_fetch_date_and_is_idempotent(tmp_path, monkeypatch):
    uni = {"id": "x", "acceptance_rate": {"value": None, "is_demo": True}, "deadlines": []}
    for f in verify.SIMPLE_FIELDS:
        uni.setdefault(f, {"value": None, "is_demo": True})
    seed = tmp_path / "universities.json"
    seed.write_text(json.dumps([uni]), encoding="utf-8")
    monkeypatch.setattr(verify, "SEED", seed)
    monkeypatch.setattr(verify, "SCORECARD", tmp_path / "scorecard")
    kept = {"x": {"gpa_avg": {**fact(3.9), "checked_at": "2026-09-17"},
                  "deadlines": [{**fact({"type": "RD", "date": "2025-01-05"}, "closing date (fall) 1/5"),
                                 "checked_at": "2026-09-17"}]}}

    verify.merge(kept)
    first = seed.read_text(encoding="utf-8")
    verify.merge(kept)
    assert seed.read_text(encoding="utf-8") == first

    merged = json.loads(first)[0]
    assert merged["gpa_avg"] == {"value": 3.9, "source_url": URL, "checked_at": "2026-09-17",
                                 "evidence": "Average high school GPA: 3.9", "is_demo": False}
    assert merged["deadlines"][0]["checked_at"] == "2026-09-17"


@pytest.mark.skipif(not verify.PAGES.exists(), reason="pipeline/out/pages is git-ignored; run cds.py first")
def test_hand_extraction_still_verifies():
    """Every fact in cds_manual.json must be found in the downloaded official document."""
    for uni_id, sources in verify.extractions().items():
        docs = verify.pages(uni_id)
        if not docs:
            continue
        for data in sources:
            for field in verify.SIMPLE_FIELDS:
                if data.get(field):
                    assert verify.is_verified(data[field], docs, field), f"{uni_id}.{field}"
            for d in data.get("deadlines", []):
                assert verify.is_verified(d, docs, "deadline"), f"{uni_id} {d['value']}"


FEES = "https://example.ac.uk/fees"
LIVING = "https://example.ac.uk/living"
FEE_DOCS = {FEES: {"text": verify.normalize("International students: £38,000 per year"), "checked_at": "2026-09-19"},
            LIVING: {"text": verify.normalize("Budget around £1 200 a month, or £15,000 for the year"),
                     "checked_at": "2026-09-19"}}
FX = {"date": "2026-09-18", "usd_per": {"USD": 1.0, "GBP": 1.33442}}


def part(kind, amount, evidence, url, currency="GBP"):
    return {"kind": kind, "amount": amount, "currency": currency, "evidence": evidence, "source_url": url}


def test_cost_is_computed_from_quoted_parts():
    item = {"parts": [part("tuition", 38000, "International students: £38,000 per year", FEES),
                      part("living", 15000, "£15,000 for the year", LIVING)]}
    cost = verify.cost_from_parts(item, FEE_DOCS, FX)
    assert cost["value"] == round(53000 * 1.33442, -2)
    assert cost["source_url"] == FEES and cost["checked_at"] == "2026-09-19"
    assert "£38,000" in cost["evidence"] and "1 GBP = 1.33442 USD" in cost["evidence"]


@pytest.mark.parametrize("parts", [
    [part("tuition", 39000, "International students: £38,000 per year", FEES)],   # amount not in the quote
    [part("tuition", 38000, "International students: £38,000 a year", FEES)],     # quote not on the page
    [part("tuition", 38000, "International students: £38,000 per year", LIVING)],  # quote on another page
    [part("tuition", 38000, "International students: £38,000 per year", FEES, "XYZ")],  # no exchange rate
    [part("living", 15000, "£15,000 for the year", LIVING)],                       # no tuition at all
    [part("tuition", 3800, "International students: £38,000 per year", FEES)],     # a prefix is not the amount
])
def test_cost_parts_rejected(parts):
    assert verify.cost_from_parts({"parts": parts}, FEE_DOCS, FX) is None


@pytest.mark.parametrize("amount, quote, ok", [
    (38000, "£38,000", True), (38000, "38 000 €", True), (38000, "EUR 38.000", True), (9535, "£9,535.00", True),
    (38000, "£380,000", False), (1000, "1,000,000", False), (38000, "38000.50", False),
])
def test_amount_in_quote(amount, quote, ok):
    assert verify.amount_in_quote(amount, quote) is ok
