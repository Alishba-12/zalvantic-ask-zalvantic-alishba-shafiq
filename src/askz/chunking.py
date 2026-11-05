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


def chunk_by_heading(text, source, max_level=3):
    # new chunk at every heading up to max_level, headings inside code fences are ignored
    sections, buf, heading, in_fence = [], [], "(intro)", False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
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
    for i, (h, body) in enumerate(sections):
        # skip sections that are only a heading with nothing under it
        if len(body.split()) <= len(h.split()) + 1 and body.lstrip().startswith("#"):
            continue
        out.append(Chunk(f"{source}#h{i}", source, h, body, "heading"))
    return out


def chunk_fixed(text, source, size=120, overlap=30):
    # sliding window over words: size words per chunk, overlap words shared with the previous chunk
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    words = text.split()
    step = size - overlap
    out = []
    for n, start in enumerate(range(0, len(words), step)):
        out.append(Chunk(f"{source}#f{n}", source, "", " ".join(words[start:start + size]), "fixed"))
        if start + size >= len(words):
            break
    return out


def build_chunks(docs, strategy, **kwargs):
    fn = {"heading": chunk_by_heading, "fixed": chunk_fixed}[strategy]
    chunks = []
    for source, text in docs.items():
        chunks.extend(fn(text, source, **kwargs))
    return chunks
