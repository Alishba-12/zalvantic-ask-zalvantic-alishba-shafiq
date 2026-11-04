"""Clean the raw Markdown files and split them into paragraph chunks (JSONL).

Usage (from the repo root):
    PYTHONPATH=src python -m askz.chunk

Output: data/processed/chunks.jsonl, one JSON object per line:
    {"id", "page", "source", "heading", "text"}
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUT_FILE = ROOT / "data" / "processed" / "chunks.jsonl"

MIN_WORDS = 4      # shorter blocks are usually menu items or buttons
MAX_CHARS = 900    # longer paragraphs are split on sentence boundaries
BOILERPLATE = {
    "home", "about", "about us", "contact", "contact us", "services", "menu", "login",
    "sign in", "get started", "read more", "learn more", "privacy policy", "terms",
    "terms of service", "skip to content", "back to top", "all rights reserved",
}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def is_noise(text: str) -> bool:
    if normalize(text) in BOILERPLATE:
        return True
    words = text.split()
    # keep short lines that carry real info, like an email address or phone number
    if len(words) < MIN_WORDS and not re.search(r"@|\d{3}", text):
        return True
    return False


def split_long(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    if len(text) <= max_chars or text.lstrip().startswith("- "):
        return [text]
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if current and len(current) + len(sentence) + 1 > max_chars:
            parts.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        parts.append(current.strip())
    return parts


def parse_markdown(md: str, fallback_source: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (source_url, [(heading, paragraph), ...]) for one raw file."""
    source, heading, items = fallback_source, "", []
    for block in re.split(r"\n\s*\n", md.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("Source:"):
            source = block.split(":", 1)[1].strip()
        elif block.startswith("#"):
            heading = block.lstrip("#").strip()
        else:
            items.append((heading, block))
    return source, items


def build_chunks(raw_dir: Path = RAW_DIR) -> list[dict]:
    chunks, seen = [], set()
    for path in sorted(raw_dir.glob("*.md")):
        source, items = parse_markdown(path.read_text(encoding="utf-8"), path.stem)
        n = 0
        for heading, block in items:
            for piece in split_long(block):
                key = normalize(piece)
                if not key or is_noise(piece) or key in seen:
                    continue
                seen.add(key)
                n += 1
                chunks.append({
                    "id": f"{path.stem}-{n:03d}",
                    "page": path.stem,
                    "source": source,
                    "heading": heading,
                    "text": piece,
                })
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw Markdown and write chunks.jsonl")
    parser.add_argument("--raw", type=Path, default=RAW_DIR)
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    args = parser.parse_args()

    chunks = build_chunks(args.raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    pages = len({c["page"] for c in chunks})
    print(f"Wrote {len(chunks)} chunks from {pages} pages to {args.out}")


if __name__ == "__main__":
    main()
