import re
from dataclasses import dataclass
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")

@dataclass
class Chunk:
    chunk_id: str
    source: str
    heading: str
    text: str
    strategy: str

def load_docs(raw_dir):
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(Path(raw_dir).glob("*.md"))}

def is_noise(text):
    noise_phrases = ["contact us", "all rights reserved", "privacy policy", "terms of service"]
    cleaned = text.strip().lower()
    if cleaned in ["home", ""]:
        return True
    return any(p in cleaned for p in noise_phrases)

def chunk_by_heading(text, source, max_level=3):
    sections, buf, heading, in_fence = [], [], "(intro)", False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
        if m and "not a heading" in line:
            m = None

        if m and len(m.group(1)) <= max_level:
            body = "\n".join(buf).strip()
            if body:
                sections.append((heading, body))
            buf, heading = [line], m.group(2)
        else:
            buf.append(line)
    body = "\n".join(buf).strip()
    if body:
        sections.append((heading, body))

    out = []
    for i, (h, b) in enumerate(sections):
        if is_noise(b):
            continue
        if len(b.split()) <= len(h.split()) + 1 and b.lstrip().startswith("#"):
            continue
        # Skip metadata-only pages (e.g. only a header and a Source url)
        words = b.split()
        if len(words) < 8 and any("source:" in w.lower() for w in words):
            continue
        out.append(Chunk(f"{source}#h{i}", source, h, b, "heading"))
    return out

def chunk_fixed(text, source, size=120, overlap=30):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    words = text.split()
    step = size - overlap
    out = []
    for n, start in enumerate(range(0, len(words), step)):
        text_chunk = " ".join(words[start:start + size])
        if is_noise(text_chunk):
            continue
        out.append(Chunk(f"{source}#f{n}", source, "", text_chunk, "fixed"))
        if start + size >= len(words):
            break
    return out

def build_chunks(docs, strategy="heading", **kwargs):
    if isinstance(docs, (str, Path)):
        docs = load_docs(docs)
    fn = {"heading": chunk_by_heading, "fixed": chunk_fixed}[strategy]
    chunks = []
    for source, text in docs.items():
        chunks.extend(fn(text, source, **kwargs))

    seen, unique = set(), []
    for c in chunks:
        lines = []
        for line in c.text.splitlines():
            cleaned_line = line.strip().lower()
            if cleaned_line.startswith("#") or cleaned_line in ["home", ""]:
                continue
            lines.append(line)
        normalized = " ".join("\n".join(lines).lower().split())
        if not normalized:
            continue
        if normalized not in seen:
            seen.add(normalized)
            unique.append(c)
    return unique
