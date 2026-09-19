"""Crawl official university pages relevant to admissions (1–2 levels, same domain).

- respects robots.txt, 1 request per second
- keeps only pages whose URL or text mentions admission / tuition / fees / requirements / deadline / international
- never crawls ranking or aggregator sites (QS, THE, Mastersportal, Niche)

Usage:  python pipeline/crawl.py [--ids mit,oxford] [--depth 2] [--max-pages 40]
        python pipeline/crawl.py --sources [--ids mit,oxford]   (only the official urls listed in sources.json)
Output: pipeline/out/pages/<university_id>/<sha1>.json  {url, fetched_at, title, text}
"""
import argparse
import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "out" / "pages"
SEED = ROOT / "supabase" / "seed" / "universities.json"
SOURCES = ROOT / "pipeline" / "sources.json"
USER_AGENT = "ApplyraBot/1.0 (hackathon research; contact via repository)"
KEYWORDS = re.compile(r"admission|apply|tuition|fees?|cost|requirement|deadline|international|english|ielts|toefl|financial.aid|scholarship|sat\b", re.I)
BLOCKED_HOSTS = ("topuniversities.com", "timeshighereducation.com", "mastersportal.com", "niche.com")
DELAY_S = 1.0
# Second-level zones under which each university has its own name (ox.ac.uk, nus.edu.sg, ...).
PUBLIC_SUFFIXES_2 = {"ac.uk", "co.uk", "ac.kr", "ac.jp", "ac.nz", "ac.at", "ac.il", "ac.in", "ac.za",
                     "edu.sg", "edu.au", "edu.hk", "edu.cn", "edu.tw", "edu.tr", "edu.my", "com.au"}


def site_root(host: str) -> str:
    """Registrable domain of a host: admissions.purdue.edu -> purdue.edu, www.ox.ac.uk -> ox.ac.uk."""
    labels = host.lower().split(":")[0].split(".")
    n = 3 if ".".join(labels[-2:]) in PUBLIC_SUFFIXES_2 else 2
    return ".".join(labels[-n:])


def same_site(host: str, root: str) -> bool:
    host = host.lower().split(":")[0]
    return host == root or host.endswith("." + root)


def allowed_by_robots(client: httpx.Client, url: str, cache: dict[str, RobotFileParser]) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in cache:
        rp = RobotFileParser()
        try:
            res = client.get(f"{base}/robots.txt", timeout=10)
            if res.status_code in (401, 403):
                rp.disallow_all = True  # same rule as RobotFileParser.read(): access denied = crawl nothing
            else:
                rp.parse(res.text.splitlines() if res.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        cache[base] = rp
    return cache[base].can_fetch(USER_AGENT, url)


def save_page(out_dir: Path, url: str, html: str) -> None:
    text = trafilatura.extract(html, include_tables=True, favor_recall=True) or ""
    meta = trafilatura.extract_metadata(html)
    record = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
              "title": meta.title if meta else None, "text": text}
    name = hashlib.sha1(url.encode()).hexdigest()[:16]
    (out_dir / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_sources(client: httpx.Client, uni_id: str, urls: list[str]) -> int:
    """Fetch exactly the listed official pages (depth 0). Pages are saved under the url as listed, so the
    source_url of a fact is the url a person can open."""
    out_dir = OUT / uni_id
    out_dir.mkdir(parents=True, exist_ok=True)
    robots: dict[str, RobotFileParser] = {}
    kept = 0
    for url in urls:
        if any(b in urlparse(url).netloc for b in BLOCKED_HOSTS):
            continue
        if not allowed_by_robots(client, url, robots):
            print(f"  - {url}: disallowed by robots.txt")
            continue
        time.sleep(DELAY_S)
        try:
            res = client.get(url, timeout=30, follow_redirects=True)
        except httpx.HTTPError as e:
            print(f"  ! {url}: {type(e).__name__}")
            continue
        if res.status_code != 200 or "text/html" not in res.headers.get("content-type", ""):
            print(f"  ! {url}: HTTP {res.status_code} {res.headers.get('content-type', '')}")
            continue
        save_page(out_dir, url, res.text)
        kept += 1
    print(f"{uni_id}: kept {kept}/{len(urls)} listed pages")
    return kept


def crawl_university(client: httpx.Client, uni: dict, depth: int, max_pages: int) -> int:
    start = uni["website"]
    root = site_root(urlparse(start).netloc)
    out_dir = OUT / uni["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    robots: dict[str, RobotFileParser] = {}
    queue = deque([(start, 0)])
    seen: set[str] = set()
    kept = 0

    while queue and len(seen) < max_pages:
        url, level = queue.popleft()
        url = urldefrag(url)[0]
        host = urlparse(url).netloc
        if url in seen or not same_site(host, root) or any(b in host for b in BLOCKED_HOSTS):
            continue
        seen.add(url)
        if not allowed_by_robots(client, url, robots):
            continue
        time.sleep(DELAY_S)
        try:
            res = client.get(url, timeout=20, follow_redirects=True)
        except httpx.HTTPError as e:
            print(f"  ! {url}: {e}")
            continue
        if res.status_code != 200 or "text/html" not in res.headers.get("content-type", ""):
            continue
        if not same_site(res.url.host, root):  # redirected off the university site
            continue

        text = trafilatura.extract(res.text, include_tables=True, favor_recall=True) or ""
        if KEYWORDS.search(url) or len(KEYWORDS.findall(text)) >= 3:
            save_page(out_dir, str(res.url), res.text)
            kept += 1

        if level < depth:
            for href in re.findall(r'href="([^"#]+)"', res.text):
                link = urljoin(str(res.url), href)
                if link.startswith("http") and KEYWORDS.search(link):
                    queue.append((link, level + 1))
    print(f"{uni['id']}: fetched {len(seen)} urls, kept {kept} pages")
    return kept


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", help="comma-separated university ids (default: all)")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--sources", action="store_true", help="fetch only the urls listed in sources.json")
    args = parser.parse_args()
    wanted = set(args.ids.split(",")) if args.ids else None

    if args.sources:
        sources = {k: v for k, v in json.loads(SOURCES.read_text(encoding="utf-8")).items() if not k.startswith("_")}
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            total = sum(fetch_sources(client, uid, urls) for uid, urls in sources.items()
                        if wanted is None or uid in wanted)
        print(f"done: {total} pages kept")
        return

    universities = json.loads(SEED.read_text(encoding="utf-8"))
    if wanted:
        universities = [u for u in universities if u["id"] in wanted]
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        total = sum(crawl_university(client, u, args.depth, args.max_pages) for u in universities)
    print(f"done: {total} pages kept for {len(universities)} universities")


if __name__ == "__main__":
    main()
