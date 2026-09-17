"""Builds universities.json / majors.json from a compact table.

The table holds approximate demo figures (is_demo=true). US rows are then overwritten with real data by
pipeline/scorecard.py + cds.py + verify.py --merge; this script keeps any row that already has verified facts.
Unknown values are None. world_rank: QS World University Rankings 2025 (approximate).
Run: python supabase/seed/build_seed.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

MAJORS = [
    ("cs", "Компьютерные науки", "Computer Science", ["11.0701"]),
    ("engineering", "Инженерия", "Engineering", ["14.0101"]),
    ("economics", "Экономика", "Economics", ["45.0601"]),
    ("business", "Бизнес и менеджмент", "Business & Management", ["52.0201"]),
    ("math", "Математика", "Mathematics", ["27.0101"]),
    ("physics", "Физика", "Physics", ["40.0801"]),
    ("biology", "Биология", "Biology", ["26.0101"]),
    ("medicine", "Медицина", "Medicine", ["51.1201"]),
    ("design", "Дизайн и архитектура", "Design & Architecture", ["50.0401", "04.0201"]),
    ("social_sciences", "Социальные науки и международные отношения", "Social Sciences & IR", ["45.0901", "45.1001"]),
]

US_DOCS = ["transcript", "essay", "recommendations", "financial_docs", "passport"]
UK_DOCS = ["transcript", "personal_statement", "recommendations", "passport"]
EU_DOCS = ["transcript", "motivation_letter", "cv", "passport"]
ASIA_DOCS = ["transcript", "motivation_letter", "recommendations", "passport"]

# id, name, country, city, website, majors, rate, (sat p25, p75) | None, gpa_avg, ielts_min, cost, aid,
# deadlines [(type, date)], extra_requirements, documents, world_rank
ROWS = [
    # --- United States -------------------------------------------------------
    ("mit", "Massachusetts Institute of Technology", "US", "Cambridge, MA", "https://mitadmissions.org",
     ["cs", "engineering", "math", "physics", "economics", "biology"], 0.045, (1520, 1580), None, 7.0, 86000, "full_need",
     [("EA", "2026-11-01"), ("RD", "2027-01-05")], [], US_DOCS, 1),
    ("harvard", "Harvard University", "US", "Cambridge, MA", "https://college.harvard.edu/admissions",
     ["cs", "economics", "math", "physics", "biology", "social_sciences"], 0.035, (1500, 1580), None, None, 87000, "full_need",
     [("REA", "2026-11-01"), ("RD", "2027-01-01")], ["Интервью с выпускником (по возможности)"], US_DOCS, 4),
    ("stanford", "Stanford University", "US", "Stanford, CA", "https://admission.stanford.edu",
     ["cs", "engineering", "economics", "math", "physics", "biology", "design"], 0.037, (1500, 1580), None, None, 89000, "full_need",
     [("REA", "2026-11-01"), ("RD", "2027-01-05")], [], US_DOCS, 6),
    ("princeton", "Princeton University", "US", "Princeton, NJ", "https://admission.princeton.edu",
     ["cs", "engineering", "economics", "math", "physics"], 0.045, (1510, 1580), 3.9, None, 83000, "full_need",
     [("REA", "2026-11-01"), ("RD", "2027-01-01")], [], US_DOCS, 22),
    ("yale", "Yale University", "US", "New Haven, CT", "https://admissions.yale.edu",
     ["cs", "economics", "math", "physics", "biology", "social_sciences"], 0.046, (1500, 1580), None, None, 88000, "full_need",
     [("REA", "2026-11-01"), ("RD", "2027-01-02")], [], US_DOCS, 23),
    ("upenn", "University of Pennsylvania", "US", "Philadelphia, PA", "https://admissions.upenn.edu",
     ["business", "economics", "cs", "engineering", "biology"], 0.059, (1500, 1570), 3.9, 7.0, 90000, "partial",
     [("ED", "2026-11-01"), ("RD", "2027-01-05")], [], US_DOCS, 11),
    ("columbia", "Columbia University", "US", "New York, NY", "https://undergrad.admissions.columbia.edu",
     ["cs", "engineering", "economics", "math", "social_sciences"], 0.039, (1500, 1570), None, None, 91000, "full_need",
     [("ED", "2026-11-01"), ("RD", "2027-01-01")], [], US_DOCS, 34),
    ("cornell", "Cornell University", "US", "Ithaca, NY", "https://admissions.cornell.edu",
     ["cs", "engineering", "business", "economics", "biology", "design"], 0.079, (1480, 1560), None, 7.0, 90000, "partial",
     [("ED", "2026-11-01"), ("RD", "2027-01-02")], [], US_DOCS, 16),
    ("uchicago", "University of Chicago", "US", "Chicago, IL", "https://collegeadmissions.uchicago.edu",
     ["economics", "math", "physics", "cs", "biology", "social_sciences"], 0.05, (1510, 1580), None, 7.0, 93000, "partial",
     [("ED", "2026-11-01"), ("EA", "2026-11-01"), ("RD", "2027-01-06")], [], US_DOCS, 21),
    ("nyu", "New York University", "US", "New York, NY", "https://www.nyu.edu/admissions",
     ["business", "economics", "cs", "design", "social_sciences"], 0.08, (1470, 1570), None, 7.5, 92000, "partial",
     [("ED", "2026-11-01"), ("RD", "2027-01-05")], [], US_DOCS, 43),
    ("umich", "University of Michigan", "US", "Ann Arbor, MI", "https://admissions.umich.edu",
     ["cs", "engineering", "business", "economics", "math", "biology"], 0.18, (1460, 1560), 3.9, 6.5, 83000, "merit_only",
     [("EA", "2026-11-01"), ("RD", "2027-02-01")], [], US_DOCS, 44),
    ("ucla", "University of California, Los Angeles", "US", "Los Angeles, CA", "https://admission.ucla.edu",
     ["cs", "engineering", "economics", "biology", "design", "social_sciences"], 0.09, None, 3.9, 7.0, 72000, "none",
     [("OTHER", "2026-11-30")], ["Personal Insight Questions (4 ответа)"], ["transcript", "essay", "passport"], 42),
    ("gatech", "Georgia Institute of Technology", "US", "Atlanta, GA", "https://admission.gatech.edu",
     ["cs", "engineering", "math", "physics", "business"], 0.17, (1370, 1530), None, 6.5, 55000, "none",
     [("EA", "2026-10-15"), ("RD", "2027-01-06")], [], US_DOCS, 114),
    ("boston_u", "Boston University", "US", "Boston, MA", "https://www.bu.edu/admissions",
     ["cs", "engineering", "business", "economics", "biology", "social_sciences"], 0.11, (1420, 1540), 3.9, 7.0, 88000, "merit_only",
     [("ED", "2026-11-01"), ("RD", "2027-01-04")], [], US_DOCS, 108),
    ("uiuc", "University of Illinois Urbana-Champaign", "US", "Champaign, IL", "https://www.admissions.illinois.edu",
     ["cs", "engineering", "business", "economics", "math", "physics"], 0.44, (1350, 1530), 3.8, 6.5, 62000, "merit_only",
     [("EA", "2026-11-01"), ("RD", "2027-01-05")], [], US_DOCS, 69),
    ("purdue", "Purdue University", "US", "West Lafayette, IN", "https://admissions.purdue.edu",
     ["engineering", "cs", "business", "math", "physics", "biology", "economics"], 0.53, (1190, 1450), 3.7, 6.5, 46000, "none",
     [("EA", "2026-11-01"), ("RD", "2027-01-15")], [], US_DOCS, 89),
    ("penn_state", "Pennsylvania State University", "US", "University Park, PA", "https://admissions.psu.edu",
     ["engineering", "business", "cs", "economics", "biology"], 0.55, (1160, 1370), 3.6, 6.5, 55000, "none",
     [("EA", "2026-11-01"), ("RD", "2026-11-30")], [], US_DOCS, 83),
    ("umn", "University of Minnesota Twin Cities", "US", "Minneapolis, MN", "https://admissions.tc.umn.edu",
     ["engineering", "cs", "business", "economics", "biology", "math"], 0.75, (1230, 1440), 3.7, 6.5, 52000, "merit_only",
     [("EA", "2026-11-01"), ("RD", "2027-01-01")], [], US_DOCS, 185),
    ("asu", "Arizona State University", "US", "Tempe, AZ", "https://admission.asu.edu",
     ["cs", "engineering", "business", "design", "biology", "social_sciences"], 0.90, (1100, 1360), 3.5, 6.0, 48000, "merit_only",
     [("RD", "2027-02-01")], [], ["transcript", "passport", "financial_docs"], 179),
    # --- United Kingdom ------------------------------------------------------
    ("oxford", "University of Oxford", "UK", "Oxford", "https://www.ox.ac.uk/admissions/undergraduate",
     ["cs", "engineering", "economics", "math", "physics", "biology", "medicine"], 0.14, None, None, 7.5, 72000, "merit_only",
     [("UCAS", "2026-10-15")], ["A-levels / IB или Foundation year", "Вступительный тест и интервью"], UK_DOCS, 3),
    ("cambridge", "University of Cambridge", "UK", "Cambridge", "https://www.undergraduate.study.cam.ac.uk",
     ["cs", "engineering", "economics", "math", "physics", "biology", "medicine", "design"], 0.18, None, None, 7.5, 75000, "merit_only",
     [("UCAS", "2026-10-15")], ["A-levels / IB или Foundation year", "Интервью"], UK_DOCS, 5),
    ("imperial", "Imperial College London", "UK", "London", "https://www.imperial.ac.uk/study/apply/undergraduate",
     ["cs", "engineering", "math", "physics", "biology", "medicine", "economics"], 0.14, None, None, 7.0, 70000, "merit_only",
     [("UCAS", "2027-01-14")], ["A-levels / IB или Foundation year"], UK_DOCS, 2),
    ("ucl", "University College London", "UK", "London", "https://www.ucl.ac.uk/prospective-students/undergraduate",
     ["cs", "engineering", "economics", "math", "physics", "biology", "design", "social_sciences"], 0.30, None, None, 7.0, 62000, "merit_only",
     [("UCAS", "2027-01-14")], ["A-levels / IB или Foundation year"], UK_DOCS, 9),
    ("lse", "London School of Economics", "UK", "London", "https://www.lse.ac.uk/study-at-lse/undergraduate",
     ["economics", "business", "math", "social_sciences"], 0.09, None, None, 7.0, 60000, "partial",
     [("UCAS", "2027-01-14")], ["A-levels / IB или Foundation year"], UK_DOCS, 50),
    ("edinburgh", "University of Edinburgh", "UK", "Edinburgh", "https://www.ed.ac.uk/studying/undergraduate",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "design", "social_sciences"], 0.40, None, None, 6.5, 50000, "merit_only",
     [("UCAS", "2027-01-14")], [], UK_DOCS, 27),
    ("manchester", "University of Manchester", "UK", "Manchester", "https://www.manchester.ac.uk/study/undergraduate",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "social_sciences"], 0.55, None, None, 6.5, 45000, "merit_only",
     [("UCAS", "2027-01-14")], [], UK_DOCS, 34),
    ("kcl", "King's College London", "UK", "London", "https://www.kcl.ac.uk/study/undergraduate",
     ["economics", "business", "cs", "biology", "medicine", "social_sciences"], 0.38, None, None, 7.0, 58000, "merit_only",
     [("UCAS", "2027-01-14")], [], UK_DOCS, 40),
    ("warwick", "University of Warwick", "UK", "Coventry", "https://warwick.ac.uk/study/undergraduate",
     ["cs", "economics", "business", "math", "physics", "engineering"], 0.30, None, None, 6.5, 52000, "merit_only",
     [("UCAS", "2027-01-14")], [], UK_DOCS, 69),
    ("leeds", "University of Leeds", "UK", "Leeds", "https://www.leeds.ac.uk/undergraduate",
     ["cs", "engineering", "economics", "business", "biology", "design", "social_sciences"], 0.70, None, None, 6.5, 42000, "merit_only",
     [("UCAS", "2027-01-14")], ["Foundation year для аттестата РК"], UK_DOCS, 82),
    # --- Netherlands ---------------------------------------------------------
    ("tudelft", "Delft University of Technology", "NL", "Delft", "https://www.tudelft.nl/en/education/admission-and-application",
     ["engineering", "cs", "math", "physics", "design"], None, None, None, 6.5, 32000, "merit_only",
     [("OTHER", "2027-01-15")], ["Отбор numerus fixus на части программ"], EU_DOCS, 49),
    ("uva", "University of Amsterdam", "NL", "Amsterdam", "https://www.uva.nl/en/education/bachelor-s",
     ["economics", "business", "cs", "social_sciences", "biology"], None, None, None, 6.5, 30000, "merit_only",
     [("OTHER", "2027-05-01")], [], EU_DOCS, 53),
    ("erasmus", "Erasmus University Rotterdam", "NL", "Rotterdam", "https://www.eur.nl/en/education/bachelor",
     ["economics", "business"], None, None, None, 6.5, 28000, "merit_only",
     [("OTHER", "2027-01-15")], [], EU_DOCS, 176),
    ("maastricht", "Maastricht University", "NL", "Maastricht", "https://www.maastrichtuniversity.nl/education/bachelor",
     ["economics", "business", "social_sciences", "medicine"], None, None, None, 6.5, 26000, "merit_only",
     [("OTHER", "2027-05-01")], [], EU_DOCS, 239),
    # --- Germany -------------------------------------------------------------
    ("tum", "Technical University of Munich", "DE", "Munich", "https://www.tum.de/en/studies/application",
     ["engineering", "cs", "math", "physics", "business"], None, None, None, 6.5, 24000, "none",
     [("OTHER", "2027-07-15")], ["Studienkolleg или 1 год вуза в РК для аттестата"], EU_DOCS, 28),
    # --- South Korea ---------------------------------------------------------
    ("kaist", "KAIST", "KR", "Daejeon", "https://admission.kaist.ac.kr/intl-undergraduate",
     ["engineering", "cs", "math", "physics", "biology", "business"], None, None, None, 6.5, 12000, "merit_only",
     [("OTHER", "2026-12-04")], [], ASIA_DOCS, 53),
    ("snu", "Seoul National University", "KR", "Seoul", "https://admission.snu.ac.kr/undergraduate/international",
     ["engineering", "cs", "economics", "business", "math", "physics", "biology", "social_sciences"], None, None, None, 6.5, 15000, "merit_only",
     [("OTHER", "2026-10-01")], [], ASIA_DOCS, 31),
    # --- Singapore -----------------------------------------------------------
    ("nus", "National University of Singapore", "SG", "Singapore", "https://www.nus.edu.sg/oam",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "design"], None, None, None, 6.5, 40000, "partial",
     [("OTHER", "2027-02-20")], ["Вступительные тесты/интервью на части программ"], ASIA_DOCS, 8),
    ("ntu", "Nanyang Technological University", "SG", "Singapore", "https://www.ntu.edu.sg/admissions/undergraduate",
     ["cs", "engineering", "business", "math", "physics", "biology", "design"], None, None, None, 6.5, 38000, "partial",
     [("OTHER", "2027-02-15")], [], ASIA_DOCS, 15),
    # --- Canada --------------------------------------------------------------
    ("utoronto", "University of Toronto", "CA", "Toronto", "https://future.utoronto.ca",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "social_sciences"], 0.43, None, None, 6.5, 58000, "merit_only",
     [("OTHER", "2027-01-15")], [], ASIA_DOCS[:1] + ["cv", "passport"], 25),
    ("ubc", "University of British Columbia", "CA", "Vancouver", "https://you.ubc.ca",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "design"], 0.52, None, None, 6.5, 55000, "merit_only",
     [("OTHER", "2027-01-15")], [], ["transcript", "essay", "passport"], 38),
    ("mcgill", "McGill University", "CA", "Montreal", "https://www.mcgill.ca/undergraduate-admissions",
     ["cs", "engineering", "economics", "business", "math", "physics", "biology", "social_sciences"], 0.40, None, None, 6.5, 50000, "merit_only",
     [("OTHER", "2027-01-15")], [], ["transcript", "passport"], 29),
    ("waterloo", "University of Waterloo", "CA", "Waterloo", "https://uwaterloo.ca/future-students",
     ["cs", "engineering", "math", "physics", "business"], 0.53, None, None, 6.5, 50000, "merit_only",
     [("OTHER", "2027-02-01")], ["Admission Information Form"], ["transcript", "cv", "passport"], 115),
]


def sourced(value, url):
    return {"value": value, "source_url": url, "checked_at": None, "evidence": None, "is_demo": True}


def build():
    universities = []
    for (uid, name, country, city, site, majors, rate, sat, gpa, ielts, cost, aid, deadlines, extra, docs, rank) in ROWS:
        universities.append({
            "id": uid, "name": name, "country": country, "city": city, "website": site, "majors": majors,
            "acceptance_rate": sourced(rate, site),
            "sat": sourced({"p25": sat[0], "p50": None, "p75": sat[1]} if sat else None, site),
            "gpa_avg": sourced(gpa, site),
            "ielts_min": sourced(ielts, site),
            "cost_per_year_usd": sourced(cost, site),
            "intl_aid": sourced(aid, site),
            "deadlines": [sourced({"type": t, "date": d}, site) for t, d in deadlines],
            "extra_requirements": extra,
            "documents": docs,
            "world_rank": rank,
        })
    # Rows that already contain pipeline-verified facts (is_demo=false) are owned by pipeline/verify.py: keep them.
    existing_path = HERE / "universities.json"
    if existing_path.exists():
        existing = {u["id"]: u for u in json.loads(existing_path.read_text(encoding="utf-8"))}
        def has_real(u: dict) -> bool:
            facts = [u[f] for f in ("acceptance_rate", "sat", "gpa_avg", "ielts_min", "cost_per_year_usd", "intl_aid")]
            return any(not f.get("is_demo", True) for f in facts + u["deadlines"])
        universities = [existing[u["id"]] if u["id"] in existing and has_real(existing[u["id"]]) else u
                        for u in universities]
    majors = [{"id": i, "name_ru": ru, "name_en": en, "cip_codes": cip} for i, ru, en, cip in MAJORS]
    (HERE / "universities.json").write_text(json.dumps(universities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "majors.json").write_text(json.dumps(majors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"universities: {len(universities)}, majors: {len(majors)}")


if __name__ == "__main__":
    build()
