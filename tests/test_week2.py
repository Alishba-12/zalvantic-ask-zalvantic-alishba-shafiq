import pytest

from askz.chunk import build_chunks, chunk_by_heading, chunk_fixed
from askz.evaluate import hit_at_k, is_relevant
from askz.bm25 import BM25Index, tokenize

DOC = """# Company
Zalvantic builds software.

## AI and Automation
We build chatbots and RAG assistants for clients.

## Web Backend
We build FastAPI backends and databases.
# not a heading
"""

def test_heading_chunks_split_on_headings():
    chunks = chunk_by_heading(DOC, "about")
    assert [c.heading for c in chunks] == ["Company", "AI and Automation", "Web Backend"]
    assert any("not a heading" in c.text for c in chunks)

def test_heading_chunks_skip_empty_sections():
    chunks = chunk_by_heading("# Only\n\n## Real\nsome text here", "x")
    assert [c.heading for c in chunks] == ["Real"]

def test_fixed_chunks_overlap_and_size():
    text = " ".join(str(i) for i in range(50))
    chunks = chunk_fixed(text, "d", size=20, overlap=5)
    assert all(len(c.text.split()) <= 20 for c in chunks)
    assert chunks[0].text.split()[-5:] == chunks[1].text.split()[:5]
    assert chunks[-1].text.split()[-1] == "49"

def test_fixed_chunks_bad_params():
    with pytest.raises(ValueError):
        chunk_fixed("a b c", "d", size=5, overlap=5)

def test_tokenize_lowercases():
    assert tokenize("Aap Kya KARTE ho?") == ["aap", "kya", "karte", "ho"]
