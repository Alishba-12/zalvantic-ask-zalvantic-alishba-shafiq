from types import SimpleNamespace

from askz.hybrid import HybridIndex, rrf


def chunk(i):
    return SimpleNamespace(id=i, text=f"text {i}", heading="h")


class Fake:
    def __init__(self, ids):
        self.ids = ids

    def search(self, query, k=5):
        return [(chunk(i), 1.0) for i in self.ids][:k]


def test_rrf_prefers_chunk_found_by_both():
    fused = rrf([[(chunk("a"), 1), (chunk("b"), 1)], [(chunk("c"), 1), (chunk("b"), 1)]])
    assert fused[0][0].id == "b"


def test_rrf_score_formula():
    fused = rrf([[(chunk("a"), 1)]], rrf_k=60)
    assert abs(fused[0][1] - 1 / 61) < 1e-9


def test_rrf_empty():
    assert rrf([[], []]) == []


def test_hybrid_returns_k_and_no_duplicates():
    h = HybridIndex([Fake(["a", "b", "c"]), Fake(["c", "d", "a"])], rrf_k=60, depth=3)
    ids = [c.id for c, _ in h.search("q", k=3)]
    assert len(ids) == 3 and len(set(ids)) == 3


def test_hybrid_depth_limits_candidates():
    h = HybridIndex([Fake(["a", "b", "c", "d"])], depth=2)
    assert [c.id for c, _ in h.search("q", k=10)] == ["a", "b"]
