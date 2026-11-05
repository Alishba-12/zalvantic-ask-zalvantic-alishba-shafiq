"""Week 4: hybrid retrieval (reciprocal rank fusion) and an optional cross-encoder reranker."""


def _key(chunk):
    return getattr(chunk, "id", None) or id(chunk)


def rrf(rankings, rrf_k=60):
    """Reciprocal rank fusion. rankings = list of [(chunk, score), ...], best first.
    Each chunk gets sum of 1 / (rrf_k + rank) over the lists it appears in."""
    scores, items = {}, {}
    for ranking in rankings:
        for rank, (chunk, _) in enumerate(ranking, 1):
            key = _key(chunk)
            items[key] = chunk
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
    order = sorted(scores, key=scores.get, reverse=True)
    return [(items[key], scores[key]) for key in order]


class HybridIndex:
    """Runs several indexes (BM25, vector, ...) and fuses their rankings with RRF."""

    def __init__(self, indexes, rrf_k=60, depth=20):
        self.indexes, self.rrf_k, self.depth = list(indexes), rrf_k, depth

    def search(self, query, k=5):
        rankings = [ix.search(query, k=self.depth) for ix in self.indexes]
        return rrf(rankings, self.rrf_k)[:k]


class RerankIndex:
    """Takes the top `pool` results of a base index and re-scores them with a cross-encoder."""

    def __init__(self, base, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2", pool=20):
        from sentence_transformers import CrossEncoder

        self.base, self.pool = base, pool
        self.model = CrossEncoder(model_name)

    def search(self, query, k=5):
        cands = self.base.search(query, k=self.pool)
        if not cands:
            return []
        pairs = [(query, f"{getattr(c, 'heading', '')} {c.text}".strip()) for c, _ in cands]
        scores = self.model.predict(pairs, show_progress_bar=False)
        ranked = sorted(zip(cands, scores), key=lambda x: x[1], reverse=True)
        return [(c, float(s)) for (c, _), s in ranked[:k]]


def final_index(chunks, depth=20, rrf_k=10):
    """The configuration chosen in week 4: BM25 + multilingual-e5-small fused with RRF."""
    from .embed import Embedder, VectorIndex
    from .search import BM25Index

    return HybridIndex([BM25Index(chunks), VectorIndex(chunks, Embedder("e5-small"))], rrf_k, depth)
