"""Normalize the openessays.org dump into the essay collection served by the backend.

Input:  data/openessays_dump/essays.jsonl   (scraped 2026-09-18; data/ is git-ignored)
Output: supabase/seed/essays.json             (committed, sorted by id; loaded into the DB by supabase/seed.py)

The dump has an empty `school` field, so the school is parsed from the title ("<kind> Essay - <school>").
Majors are mapped from the free-text `program` onto the catalog major ids by keywords.

Usage:  python pipeline/essays.py
"""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "openessays_dump" / "essays.jsonl"
OUT = ROOT / "supabase" / "seed" / "essays.json"

LEVELS = {"BACHELORS": "bachelor", "POST_GRAD": "master", "PHD": "phd", "MBA": "mba"}

SCHOOL_ALIASES = {"Cornell": "Cornell University", "New York U niversity": "New York University", "Unknown": None}

# School name (after aliases) → catalog university id.
UNIVERSITY_IDS = {
    "MIT": "mit", "Harvard University": "harvard", "Stanford University": "stanford", "Princeton": "princeton",
    "Yale University": "yale", "University of Pennsylvania": "upenn", "Columbia University": "columbia",
    "Cornell University": "cornell", "University of Chicago": "uchicago", "New York University": "nyu",
    "University of Michigan": "umich", "Georgia Institute of Technology": "gatech",
    "University of Illinois Urbana-Champaign": "uiuc", "University of Oxford": "oxford",
    "UCL (University College London)": "ucl", "University of Toronto": "utoronto",
    "University of British Columbia": "ubc", "ETH Zurich": "ethz",
}

MAJOR_KEYWORDS = {
    "cs": r"\b(NLP|ML|CV|HCI|PL|DB|AI|RL|CS|CSE|Systems|Security|Cryptography|Graphics|Theory|Formal Methods|"
          r"Software|Computer|Data Science|Information Sciences|Social Computing|Speech|Robotics)\b",
    "engineering": r"\b(Robotics|Software Engineering|Operations Research|Complex Adaptive Systems|Medical Imaging)\b",
    "math": r"\b(Statistics|Math\w*|Theory|Operations Research|Cryptography|Formal Methods)\b",
    "physics": r"\bPhysics\b",
    "biology": r"(Biology|Neuro|Genetics|Genomics|Molecular)",
    "medicine": r"\b(Medicine|Public Health|Medical)\b",
    "economics": r"\bEconomics\b",
    "business": r"\b(MBA|Business)\b",
    "social_sciences": r"\b(Law|LLB|Policy|Race|Ethnicity|History|Education|Social Science|Psychology|Cognitive|"
                       r"Media|Communication|East Asian|Linguistics|Human behavior)\b",
}

# Degree words stripped from `program` before splitting it into topic chips.
DEGREE_PREFIX = re.compile(
    r"^(Ph\.?D\.?( Program in)?|Bachelor'?s?( Degree| of Science| of| in)?|Master of Science in|Masters? in|"
    r"MBA|Msc|BS|BA|MS)(?=[\s,]|$)[\s,]*", re.IGNORECASE)
TOPIC_ALIASES = {"CS": "Computer Science"}
NO_TOPIC = {"", "Unknown", "Undecided", "Science", "Graduate School of Education"}


def parse_title(title: str) -> tuple[str, str | None]:
    head, _, school = title.rpartition(" Essay - ")
    school = school.strip()
    return head.strip(), SCHOOL_ALIASES.get(school, school)


def essay_kind(head: str) -> str:
    h = head.lower()
    if h.startswith("common app"):
        return "common_app"
    if "personal statement" in h:
        return "personal_statement"
    if h.startswith(("statement of purpose", "statement of intent")):
        return "statement_of_purpose"
    return "other"


def topics(program: str) -> list[str]:
    rest = DEGREE_PREFIX.sub("", program.strip())
    out: list[str] = []
    for part in re.split(r",|/", rest):
        part = part.strip()
        words = part.split()
        # "NLP ML Systems" is a list of abbreviations, "Computer Vision" is one topic.
        chunks = words if len(words) > 1 and all(w.isupper() or w == "Systems" for w in words) else [part]
        for c in chunks:
            c = TOPIC_ALIASES.get(c, c)
            if c not in NO_TOPIC and c not in out:
                out.append(c)
    return out


def clean_body(body: str, attribution: str) -> str:
    text = body.strip()
    first, _, rest = text.partition("\n")
    if first.strip().lower() == attribution.strip().lower() or first.lower().startswith("public success story"):
        text = rest.strip()
    return re.sub(r"\n{3,}", "\n\n", text)


def excerpt(body: str, words: int = 45) -> str:
    tokens = body.split()
    return " ".join(tokens[:words]) + ("…" if len(tokens) > words else "")


def normalize(row: dict) -> dict:
    head, school = parse_title(row["title"])
    author = re.search(r"\((.+)\)\s*$", row["source_attribution"] or "")
    body = clean_body(row["body"], row["source_attribution"] or "")
    program = row["program"].strip()
    majors = [m for m, pattern in MAJOR_KEYWORDS.items() if re.search(pattern, program, re.IGNORECASE if m != "cs" else 0)]
    return {
        "id": row["slug"],
        "school": school,
        "university_id": UNIVERSITY_IDS.get(school or ""),
        "level": LEVELS.get(row["essay_type"], "other"),
        "kind": essay_kind(head),
        "prompt": head if essay_kind(head) == "other" and len(head) > 30 else None,
        "program": None if program in ("", "Unknown") else program,
        "majors": majors,
        "topics": topics(program),
        "author": author.group(1).strip() if author else None,
        "license": row["license"] if row["license"] == "CC_BY_NC_SA_4_0" else "UNKNOWN",
        "source_url": row["url"],
        "original_url": row["original_link"] or None,
        "word_count": int(row["word_count"] or len(body.split())),
        "excerpt": excerpt(body),
        "body": body,
        "references": row.get("references") or [],
    }


def main() -> None:
    rows = [json.loads(line) for line in SRC.read_text(encoding="utf-8").splitlines() if line.strip()]
    essays = sorted((normalize(r) for r in rows), key=lambda e: e["id"])
    OUT.write_text(json.dumps(essays, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"essays: {len(essays)} -> {OUT.relative_to(ROOT)}")
    print("by level:", dict(collections.Counter(e["level"] for e in essays)))
    print("by kind:", dict(collections.Counter(e["kind"] for e in essays)))
    print("matched to catalog:", sum(e["university_id"] is not None for e in essays),
          dict(collections.Counter(e["university_id"] for e in essays if e["university_id"])))
    print("no major:", [e["id"] for e in essays if not e["majors"]])


if __name__ == "__main__":
    main()
