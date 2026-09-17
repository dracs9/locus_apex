"""Import acceptance rate, SAT range and cost for US universities from the College Scorecard API
(U.S. Department of Education, IPEDS data). Values come straight from the API, so they are stored with
is_demo=false and the raw field values as evidence.

Usage:  python pipeline/scorecard.py            (SCORECARD_API_KEY env var, falls back to api.data.gov DEMO_KEY)
Input:  pipeline/us_unitids.json  {university_id: IPEDS unitid}, checked by hand against school name + city
Output: pipeline/out/scorecard/<university_id>.json  {field: Sourced}
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
IDS = ROOT / "pipeline" / "us_unitids.json"
OUT = ROOT / "pipeline" / "out" / "scorecard"
API = "https://api.data.gov/ed/collegescorecard/v1/schools"

RATE = "latest.admissions.admission_rate.overall"
SAT = "latest.admissions.sat_scores.{pct}_percentile.{part}"
COA = "latest.cost.attendance.academic_year"
TUITION_IN = "latest.cost.tuition.in_state"
TUITION_OUT = "latest.cost.tuition.out_of_state"
SAT_FIELDS = [SAT.format(pct=p, part=s) for p in ("25th", "75th") for s in ("critical_reading", "math")]
FIELDS = ["id", "school.name", RATE, COA, TUITION_IN, TUITION_OUT, *SAT_FIELDS]


def sourced(value, unitid: int, evidence: str) -> dict:
    return {"value": value, "source_url": f"https://collegescorecard.ed.gov/school/?{unitid}",
            "checked_at": date.today().isoformat(), "evidence": f"College Scorecard API (latest): {evidence}",
            "is_demo": False}


def convert(row: dict) -> dict:
    uid = row["id"]
    out: dict = {}
    if row.get(RATE) is not None:
        out["acceptance_rate"] = sourced(round(row[RATE], 4), uid, f"{RATE}={row[RATE]}")

    sat = {f: row.get(f) for f in SAT_FIELDS}
    if all(v is not None for v in sat.values()):
        p25 = sat[SAT_FIELDS[0]] + sat[SAT_FIELDS[1]]
        p75 = sat[SAT_FIELDS[2]] + sat[SAT_FIELDS[3]]
        out["sat"] = sourced({"p25": p25, "p50": None, "p75": p75}, uid,
                             "; ".join(f"{k.split('sat_scores.')[1]}={v}" for k, v in sat.items()) + " (reading + math)")

    coa, t_in, t_out = row.get(COA), row.get(TUITION_IN), row.get(TUITION_OUT)
    if coa is not None and t_in is not None and t_out is not None:
        # Cost of attendance is published for in-state students; international students pay out-of-state tuition.
        cost = int(coa - t_in + t_out)
        out["cost_per_year_usd"] = sourced(cost, uid, f"{COA}={coa}; {TUITION_IN}={t_in}; {TUITION_OUT}={t_out} "
                                                      "(attendance − in-state tuition + out-of-state tuition)")
    return out


def main() -> None:
    ids: dict[str, int] = json.loads(IDS.read_text(encoding="utf-8"))
    key = os.environ.get("SCORECARD_API_KEY", "DEMO_KEY")
    res = httpx.get(API, params={"api_key": key, "id": ",".join(str(v) for v in ids.values()),
                                 "fields": ",".join(FIELDS), "per_page": 100}, timeout=30)
    res.raise_for_status()
    rows = {r["id"]: r for r in res.json()["results"]}

    OUT.mkdir(parents=True, exist_ok=True)
    missing_total = 0
    for uni_id, unitid in sorted(ids.items()):
        row = rows.get(unitid)
        if row is None:
            print(f"! {uni_id}: unitid {unitid} not returned", file=sys.stderr)
            continue
        data = convert(row)
        missing = [f for f in ("acceptance_rate", "sat", "cost_per_year_usd") if f not in data]
        missing_total += len(missing)
        (OUT / f"{uni_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{uni_id:12} {row['school.name']}: {len(data)} fields" + (f" (not published: {', '.join(missing)})" if missing else ""))
    print(f"done: {len(rows)} schools, {missing_total} fields not published")


if __name__ == "__main__":
    main()
