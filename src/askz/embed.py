"""Embedding models and a FAISS vector index (week 3)."""
import numpy as np

MODELS = {
    "minilm": {
        "label": "all-MiniLM-L6-v2",
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "",
        "passage_prefix": "",
    },
    "e5-small": {
        "label": "multilingual-e5-small",
        "name": "intfloat/multilingual-e5-small",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
}


class Embedder:
    """Wraps a sentence-transformers model. Vectors are normalised, so inner product = cosine."""

    def __init__(self, key):
        from sentence_transformers import SentenceTransformer

        self.key = key
        self.cfg = MODELS[key]
        self.model = SentenceTransformer(self.cfg["name"])

    def encode(self, texts, kind="passage"):
        prefix = self.cfg["query_prefix"] if kind == "query" else self.cfg["passage_prefix"]
        vecs = self.model.encode(
            [prefix + t for t in texts],
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return np.asarray(vecs, dtype="float32")


class VectorIndex:
    """FAISS flat index over Chunk objects. search() returns [(chunk, score), ...] like BM25Index."""

    def __init__(self, chunks, embedder):
        import faiss

        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("cannot build an index with no chunks")
        self.embedder = embedder
        vecs = embedder.encode([c.text for c in self.chunks], "passage")
        self.index = faiss.IndexFlatIP(vecs.shape[1])
        self.index.add(vecs)

    def search(self, query, k=5):
        q = self.embedder.encode([query], "query")
        scores, ids = self.index.search(q, min(k, len(self.chunks)))
        return [(self.chunks[i], float(s)) for s, i in zip(scores[0], ids[0]) if i != -1]
