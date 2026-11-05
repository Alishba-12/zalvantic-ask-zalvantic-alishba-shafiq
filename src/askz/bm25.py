import re
from rank_bm25 import BM25Okapi

def tokenize(text):
    return re.findall(r"\w+", text.lower())

class BM25Index:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("cannot build an index with no chunks")
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def search(self, query, k=3, top=None):
        # Handle both 'k' (Week 2) and 'top' (Week 1 pipeline tests) parameters
        limit = top if top is not None else k
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:limit]
        return [(self.chunks[i], float(scores[i])) for i in order]

# Alias BM25 to BM25Index for backwards compatibility
BM25 = BM25Index
