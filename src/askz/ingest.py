"""Download public pages from zalvantic.com and save them as Markdown in data/raw/.

Usage (from the repo root):
    PYTHONPATH=src python -m askz.ingest
    PYTHONPATH=src python -m askz.ingest --base https://zalvantic.com --max-pages 40

Notes:
- Only public pages are fetched, robots.txt is respected, and there is a small delay
  between requests so the website is not hammered.
- Menus, footers, scripts and forms are dropped here. Duplicate paragraphs are removed
  later in chunk.py.
"""
import argparse
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
HEADERS = {"User-Agent": "askz-student-project/0.1 (internship learning project)"}
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe", "button"]
NOISE_HINT = re.compile(r"(menu|navbar|nav-|cookie|breadcrumb|sidebar|newsletter)", re.I)
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".zip",
            ".mp4", ".css", ".js", ".ico", ".xml", ".txt")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slugify(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    return slug or "home"


def host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def html_to_markdown(html: str, url: str) -> str:
    """Turn one HTML page into simple Markdown (title, headings, paragraphs, bullet lists)."""
    soup = BeautifulSoup(html, "html.parser")
    title = clean_text(soup.title.get_text()) if soup.title else slugify(url)

    for tag in soup(NOISE_TAGS):
        tag.decompose()
    hinted = soup.find_all(attrs={"class": NOISE_HINT}) + soup.find_all(attrs={"id": NOISE_HINT})
    for el in hinted:
        if el.name in ("html", "body", "main") or getattr(el, "decomposed", False):
            continue
        el.decompose()

    blocks, seen = [], set()
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        if el.name == "p" and el.find_parent("li"):
            continue  # the <li> already contains this text
        text = clean_text(el.get_text(" "))
        if not text or text in seen:
            continue
        seen.add(text)
        if el.name in ("h1", "h2"):
            blocks.append(("h", f"## {text}"))
        elif el.name == "h3":
            blocks.append(("h", f"### {text}"))
        elif el.name == "h4":
            blocks.append(("h", f"#### {text}"))
        elif el.name == "li":
            blocks.append(("li", f"- {text}"))
        else:
            blocks.append(("p", text))

    out = [f"# {title}", "", f"Source: {url}", ""]
    prev = None
    for kind, text in blocks:
        if kind == "li" and prev == "li":
            out.append(text)  # keep list items together
        else:
            if out and out[-1] != "":
                out.append("")
            out.append(text)
        prev = kind
    return "\n".join(out).strip() + "\n"


def find_links(html: str, page_url: str, base_host: str) -> list[str]:
    """Return internal links found on a page (no fragments, queries or file downloads)."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full, _ = urldefrag(urljoin(page_url, href))
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https") or host(full) != base_host:
            continue
        if parsed.path.lower().endswith(SKIP_EXT):
            continue
        links.append(parsed._replace(query="").geturl().rstrip("/") or full)
    return links


def sitemap_urls(base: str) -> list[str]:
    try:
        resp = requests.get(urljoin(base, "/sitemap.xml"), headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        return [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    except Exception:
        return []


def crawl(base: str, max_pages: int, delay: float) -> dict[str, str]:
    base = base.rstrip("/")
    base_host = host(base)
    rp = robotparser.RobotFileParser()
    try:
        resp = requests.get(urljoin(base, "/robots.txt"), headers=HEADERS, timeout=20)
        rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except Exception:
        rp.parse([])
    rp.modified()  # tells the parser the rules are loaded, otherwise it blocks everything

    queue = deque([base] + [u for u in sitemap_urls(base) if host(u) == base_host])
    visited, pages = set(), {}
    while queue and len(pages) < max_pages:
        url = queue.popleft().rstrip("/")
        if url in visited:
            continue
        visited.add(url)
        if not rp.can_fetch(HEADERS["User-Agent"], url):
            print(f"  skipped (robots.txt): {url}")
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as exc:
            print(f"  failed: {url} ({exc})")
            continue
        if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", ""):
            print(f"  skipped ({resp.status_code}): {url}")
            continue
        pages[url] = resp.text
        print(f"  fetched: {url}")
        for link in find_links(resp.text, url, base_host):
            if link not in visited:
                queue.append(link)
        time.sleep(delay)
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public Zalvantic pages as Markdown.")
    parser.add_argument("--base", default="https://zalvantic.com")
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pages = crawl(args.base, args.max_pages, args.delay)
    if not pages:
        print("No pages fetched. Check the URL or your internet connection.")
        return
    for url, html in pages.items():
        md = html_to_markdown(html, url)
        path = RAW_DIR / f"{slugify(url)}.md"
        path.write_text(md, encoding="utf-8")
        words = len(md.split())
        flag = "  <-- very little text, the page may be rendered by JavaScript" if words < 60 else ""
        print(f"saved {path.name} ({words} words){flag}")
    print(f"\nDone: {len(pages)} pages saved in {RAW_DIR}")


if __name__ == "__main__":
    main()
