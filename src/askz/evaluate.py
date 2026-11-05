import argparse
import json
from pathlib import Path

from .chunking import build_chunks, load_docs
from .search import BM25Index

SRC_KEYS = ("source", "expected_source", "doc")
KW_KEYS = ("keywords", "expected_keywords", "answer_keywords")
Q_KEYS = ("question", "q", "query")

def _first(d, keys, default=None):
    for k in keys:
        if d.get(k):
            return d[k]
    return default

def load_questions(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("questions", data)
    return data

def is_relevant(chunk, q):
    src = _first(q, SRC_KEYS)
    kws = _first(q, KW_KEYS, [])
    if isinstance(kws, str):
        kws = [kws]
    if not src and not kws:
        raise ValueError("question has no source or keywords to judge hits: %r" % (q,))
    ok = True
    if src:
        ok = ok and chunk.source == Path(src).stem
    if kws:
        low = chunk.text.lower()
        ok = ok and any(k.lower() in low for k in kws)
    return ok

def hit_at_k(index, questions, k=3):
    hits, misses = 0, []
    for q in questions:
        text = _first(q, Q_KEYS)
        top = index.search(text, k=k)
        if any(is_relevant(c, q) for c, _ in top):
            hits += 1
        else:
            misses.append(text)
    return (hits / len(questions) if questions else 0.0), misses

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--size", type=int, default=120)
    ap.add_argument("--overlap", type=int, default=30)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out", default="eval/week2_results.json")
    a = ap.parse_args(argv)

    docs = load_docs(a.raw_dir)
    questions = load_questions(a.questions)
    configs = {"heading": {}, "fixed": {"size": a.size, "overlap": a.overlap}}
    results = {}
    print(f"{len(questions)} questions, {len(docs)} documents")
    print(f"{'strategy':<10}{'chunks':>8}{'hit@' + str(a.k):>9}")
    for name, kw in configs.items():
        chunks = build_chunks(docs, name, **kw)
        score, misses = hit_at_k(BM25Index(chunks), questions, a.k)
        results[name] = {"chunks": len(chunks), f"hit@{a.k}": round(score, 4), "misses": misses, "params": kw}
        print(f"{name:<10}{len(chunks):>8}{score:>9.3f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results

if __name__ == "__main__":
    main()
