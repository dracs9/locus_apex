"""Download official Common Data Set files (PDF or XLSX) from each university's own institutional-research site
and store their text in the crawl format, so extract.py / verify.py can use them.

Only official university domains are listed in cds_sources.json. Sites that block automated downloads (HTTP 403)
or require a login are skipped, never worked around.

Usage:  python pipeline/cds.py [--ids harvard,purdue]
Output: pipeline/out/pages/<university_id>/cds-<n>.json  {url, fetched_at, title, text}
"""
import argparse
import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import httpx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "pipeline" / "cds_sources.json"
OUT = ROOT / "pipeline" / "out" / "pages"
USER_AGENT = "Mozilla/5.0 (compatible; ApplyraBot/1.0; hackathon research on public Common Data Sets)"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def xlsx_text(data: bytes) -> str:
    """Plain-text dump of every sheet: one line per row, cells separated by ' | '."""
    zf = zipfile.ZipFile(io.BytesIO(data))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]
    lines: list[str] = []
    sheets = sorted((n for n in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                    key=lambda n: int(re.findall(r"\d+", n)[0]))
    for name in sheets:
        root = ElementTree.fromstring(zf.read(name))
        for row in root.iter(f"{{{NS['m']}}}row"):
            cells = []
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                inline = c.find("m:is", NS)
                if c.get("t") == "s" and v is not None:
                    cells.append(shared[int(v.text)])
                elif inline is not None:
                    cells.append("".join(t.text or "" for t in inline.iter(f"{{{NS['m']}}}t")))
                elif v is not None and v.text:
                    cells.append(v.text)
            cells = [x.strip() for x in cells if x and x.strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids")
    args = parser.parse_args()
    sources: dict = json.loads(SOURCES.read_text(encoding="utf-8"))
    if args.ids:
        sources = {k: v for k, v in sources.items() if k in set(args.ids.split(","))}

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60) as client:
        for uni_id, src in sorted(sources.items()):
            out_dir = OUT / uni_id
            out_dir.mkdir(parents=True, exist_ok=True)
            for n, url in enumerate(src["urls"]):
                time.sleep(1)
                try:
                    res = client.get(url)
                except httpx.HTTPError as e:
                    print(f"! {uni_id}: {type(e).__name__} for {url} (skipped)")
                    continue
                if res.status_code != 200:
                    print(f"! {uni_id}: HTTP {res.status_code} for {url} (skipped)")
                    continue
                is_xlsx = url.lower().endswith(".xlsx") or "spreadsheetml" in res.headers.get("content-type", "")
                try:
                    text = xlsx_text(res.content) if is_xlsx else pdf_text(res.content)
                except Exception as e:  # not a real PDF/XLSX (e.g. an HTML error page with status 200)
                    print(f"! {uni_id}: cannot parse {url} ({type(e).__name__}: {e}) (skipped)")
                    continue
                record = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
                          "title": f"Common Data Set {src['year']}", "text": text}
                (out_dir / f"cds-{n}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"{uni_id}: {src['year']} {'xlsx' if is_xlsx else 'pdf'} → {len(text):,} chars")


if __name__ == "__main__":
    main()
