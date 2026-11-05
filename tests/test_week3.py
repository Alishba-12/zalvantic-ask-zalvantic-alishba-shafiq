import numpy as np
import pytest

from askz.chunking import Chunk
from askz.compare import first_ranks, markdown_table, mrr, recall_at, summarise, update_benchmark
from askz.embed import VectorIndex


def make_chunks():
    return [
        Chunk("d#h0", "d", "A", "alpha text", "heading"),
        Chunk("d#h1", "d", "B", "beta text", "heading"),
        Chunk("d#h2", "d", "C", "gamma text", "heading"),
    ]


class FixedOrderIndex:
    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, k=5):
        return [(c, 1.0) for c in self.chunks][:k]


QS = [
    {"question": "q1", "language": "en", "keywords": ["beta"]},
    {"question": "q2", "language": "en", "keywords": ["alpha"]},
    {"question": "q3", "language": "roman_ur", "keywords": ["zzz"]},
]


def test_first_ranks_and_metrics():
    ranks = first_ranks(FixedOrderIndex(make_chunks()), QS, k=10)
    assert ranks == [2, 1, None]
    assert recall_at(ranks, 1) == pytest.approx(1 / 3)
    assert recall_at(ranks, 5) == pytest.approx(2 / 3)
    assert mrr(ranks) == pytest.approx((0.5 + 1.0) / 3)


def test_summarise_splits_languages():
    out = summarise(QS, [2, 1, None])
    assert out["all"]["n"] == 3 and out["english"]["n"] == 2 and out["roman_urdu"]["n"] == 1
    assert out["english"]["recall@5"] == 1.0
    assert out["roman_urdu"]["mrr"] == 0.0


def test_markdown_table_has_one_row_per_system():
    table = markdown_table({"BM25": summarise(QS, [2, 1, None]), "model": summarise(QS, [1, 1, 1])})
    assert len(table.splitlines()) == 4


def test_update_benchmark_keeps_notes_outside_markers(tmp_path):
    p = tmp_path / "benchmark.md"
    p.write_text("# Week 2\n\nold text\n", encoding="utf-8")
    update_benchmark(p, "intro one", "TABLE ONE")
    p.write_text(p.read_text(encoding="utf-8") + "\nMy notes.\n", encoding="utf-8")
    update_benchmark(p, "intro two", "TABLE TWO")
    text = p.read_text(encoding="utf-8")
    assert "old text" in text and "My notes." in text
    assert "TABLE TWO" in text and "TABLE ONE" not in text


class FakeEmbedder:
    VOCAB = ["chatbot", "api", "design", "mobile"]

    def encode(self, texts, kind="passage"):
        vecs = np.array([[t.lower().count(w) for w in self.VOCAB] for t in texts], dtype="float32") + 1e-3
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def test_vector_index_returns_closest_chunk_first():
    pytest.importorskip("faiss")
    chunks = [
        Chunk("d#h0", "d", "A", "we build a chatbot chatbot", "heading"),
        Chunk("d#h1", "d", "B", "we build an api api", "heading"),
        Chunk("d#h2", "d", "C", "we do design design", "heading"),
    ]
    top = VectorIndex(chunks, FakeEmbedder()).search("chatbot", k=2)
    assert top[0][0].heading == "A"
    assert len(top) == 2
