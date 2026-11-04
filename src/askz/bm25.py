"""Simple command-line search over the cleaned chunks, using BM25 (no extra libraries).

Usage (from the repo root):
    PYTHONPATH=src python -m askz.bm25 "What services do you offer?"
    PYTHONPATH=src python -m askz.bm25 "Aap kitne din mein project complete karte hain?" --top 3
    PYTHONPATH=src python -m askz.bm25 --eval        # check eval/questions.json (hit@1, hit@3)
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = ROOT / "data" / "processed" / "chunks.jsonl"
QUESTIONS_FILE = ROOT / "eval" / "questions.json"

# Small stop word list: English plus common Roman Urdu filler words.
STOPWORDS = set("""
a an the and or of to in on for with is are was were be do does did can could would will you your we our us
i me my it this that these those at by from as about what how which who when where why any have has
aap ap hai hain ho hota hoti hote ka ki ke ko se mein me par pe kya kia kaise kaisay kab kahan kyun kyon
kitna kitni kitne aur ya bhi to toh ye yeh wo woh hum hamara hamari main mujhe mera meri kar karte karta
karna kar sakte sakta sakti chahiye chahta chahti raha rahe rahi
""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        # the heading is part of the searchable text, it often names the topic
        self.docs = [tokenize(f"{c.get('heading', '')} {c['text']}") for c in chunks]
        self.freqs = [Counter(d) for d in self.docs]
        self.avg_len = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        df = Counter(term for d in self.docs for term in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_tokens: list[str], i: int) -> float:
        freq, length, total = self.freqs[i], len(self.docs[i]), 0.0
        for t in query_tokens:
            if t not in freq:
                continue
            tf = freq[t]
            denom = tf + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
            total += self.idf[t] * tf * (self.k1 + 1) / denom
        return total

    def search(self, query: str, top: int = 1) -> list[tuple[float, dict]]:
        tokens = tokenize(query)
        scored = [(self.score(tokens, i), c) for i, c in enumerate(self.chunks)]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda s: s[0], reverse=True)
        return scored[:top]


def load_chunks(path: Path = CHUNKS_FILE) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found. Run ingest.py and chunk.py first.")
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def source_matches(expected: str, chunk: dict) -> bool:
    expected = expected.strip().rstrip("/")
    return expected in (chunk["page"], chunk["id"]) or chunk["source"].rstrip("/").endswith(expected)


def run_eval(index: BM25, path: Path = QUESTIONS_FILE) -> None:
    questions = json.loads(path.read_text(encoding="utf-8"))
    scored = [q for q in questions if q.get("expected_source")]
    if not scored:
        print("No questions with expected_source yet, fill them in first.")
        return
    hit1 = hit3 = 0
    for q in scored:
        results = index.search(q["question"], top=3)
        ok1 = bool(results) and source_matches(q["expected_source"], results[0][1])
        ok3 = any(source_matches(q["expected_source"], c) for _, c in results)
        hit1 += ok1
        hit3 += ok3
        if not ok3:
            print(f"MISS  [{q['id']}] {q['question']}  (expected {q['expected_source']})")
    n = len(scored)
    print(f"\nQuestions checked: {n}   hit@1: {hit1 / n:.2f}   hit@3: {hit3 / n:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the Zalvantic knowledge base.")
    parser.add_argument("question", nargs="?", help="your question, in English or Roman Urdu")
    parser.add_argument("--top", type=int, default=1, help="how many paragraphs to print")
    parser.add_argument("--eval", action="store_true", help="run eval/questions.json")
    parser.add_argument("--chunks", type=Path, default=CHUNKS_FILE)
    args = parser.parse_args()

    index = BM25(load_chunks(args.chunks))
    if args.eval:
        run_eval(index)
        return
    if not args.question:
        parser.error("please give a question, or use --eval")

    results = index.search(args.question, top=args.top)
    if not results:
        print("No relevant paragraph found.")
        return
    for rank, (score, chunk) in enumerate(results, start=1):
        label = "Best match" if rank == 1 else f"Match {rank}"
        where = f"{chunk['page']} > {chunk['heading']}" if chunk["heading"] else chunk["page"]
        print(f"{label} (score {score:.2f}) | {where}")
        print(chunk["text"])
        print(f"Source: {chunk['source']}\n")


if __name__ == "__main__":
    main()
