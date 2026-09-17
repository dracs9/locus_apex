"""Crawl official university pages relevant to admissions (1–2 levels, same domain).

- respects robots.txt, 1 request per second
- keeps only pages whose URL or text mentions admission / tuition / fees / requirements / deadline / international
- never crawls ranking or aggregator sites (QS, THE, Mastersportal, Niche)

Usage:  python pipeline/crawl.py [--ids mit,oxford] [--depth 2] [--max-pages 40]
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
USER_AGENT = "AdmissionRouteBot/1.0 (hackathon research; contact via repository)"
KEYWORDS = re.compile(r"admission|apply|tuition|fees?|cost|requirement|deadline|international|english|ielts|toefl|financial.aid|scholarship|sat\b", re.I)
BLOCKED_HOSTS = ("topuniversities.com", "timeshighereducation.com", "mastersportal.com", "niche.com")
DELAY_S = 1.0


def allowed_by_robots(client: httpx.Client, url: str, cache: dict[str, RobotFileParser]) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in cache:
        rp = RobotFileParser()
        try:
            res = client.get(f"{base}/robots.txt", timeout=10)
            rp.parse(res.text.splitlines() if res.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        cache[base] = rp
    return cache[base].can_fetch(USER_AGENT, url)


def crawl_university(client: httpx.Client, uni: dict, depth: int, max_pages: int) -> int:
    start = uni["website"]
    domain = urlparse(start).netloc.split(":")[0]
    root_domain = ".".join(domain.split(".")[-2:])
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
        if url in seen or not host.endswith(root_domain) or any(b in host for b in BLOCKED_HOSTS):
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

        text = trafilatura.extract(res.text, include_tables=True, favor_recall=True) or ""
        if KEYWORDS.search(url) or len(KEYWORDS.findall(text)) >= 3:
            meta = trafilatura.extract_metadata(res.text)
            record = {"url": str(res.url), "fetched_at": datetime.now(timezone.utc).isoformat(),
                      "title": meta.title if meta else None, "text": text}
            name = hashlib.sha1(str(res.url).encode()).hexdigest()[:16]
            (out_dir / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
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
    args = parser.parse_args()

    universities = json.loads(SEED.read_text(encoding="utf-8"))
    if args.ids:
        wanted = set(args.ids.split(","))
        universities = [u for u in universities if u["id"] in wanted]
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        total = sum(crawl_university(client, u, args.depth, args.max_pages) for u in universities)
    print(f"done: {total} pages kept for {len(universities)} universities")


if __name__ == "__main__":
    main()
