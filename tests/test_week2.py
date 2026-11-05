import pytest

from askz.chunking import build_chunks, chunk_by_heading, chunk_fixed
from askz.evaluate import hit_at_k, is_relevant
from askz.search import BM25Index, tokenize

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
    assert "# not a heading" in chunks[-1].text


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


def test_bm25_ranks_relevant_chunk_first():
    chunks = build_chunks({"about": DOC}, "heading")
    top = BM25Index(chunks).search("do you build chatbots", k=3)
    assert top[0][0].heading == "AI and Automation"
    assert len(top) == 3


def test_hit_at_k_counts_hits_and_misses():
    index = BM25Index(build_chunks({"about": DOC}, "heading"))
    qs = [
        {"question": "who builds chatbots", "source": "about", "keywords": ["chatbots"]},
        {"question": "fastapi database", "keywords": ["fastapi"]},
        {"question": "chatbots", "keywords": ["pizza"]},
    ]
    score, misses = hit_at_k(index, qs, k=3)
    assert score == pytest.approx(2 / 3)
    assert misses == ["chatbots"]


def test_is_relevant_needs_a_gold_label():
    chunk = build_chunks({"about": DOC}, "heading")[0]
    with pytest.raises(ValueError):
        is_relevant(chunk, {"question": "hi"})