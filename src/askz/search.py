import re

from rank_bm25 import BM25Okapi


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class BM25Index:
    """BM25 over Chunk objects (week 2). search() returns [(chunk, score), ...]."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("cannot build an index with no chunks")
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def search(self, query, k=3):
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]
