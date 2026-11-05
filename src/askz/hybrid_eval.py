"""Week 4: BM25 vs vectors vs hybrid (RRF) vs hybrid + rerank. Writes eval/week4_results.json and docs/benchmark.md."""
import argparse
import json
import re
import time
from pathlib import Path

from .chunking import build_chunks, load_docs
from .compare import first_ranks, summarise
from .embed import MODELS, Embedder, VectorIndex
from .evaluate import Q_KEYS, _first, load_questions
from .hybrid import HybridIndex, RerankIndex
from .search import BM25Index

START, END = "<!-- week4-table:start -->", "<!-- week4-table:end -->"


def markdown_table(results):
    head = "| System | R@5 all | R@5 English | R@5 Roman Urdu | MRR all | ms / query |\n|---|---|---|---|---|---|\n"
    rows = []
    for name, r in results.items():
        rows.append(
            f"| {name} | {r['all']['recall@5']:.3f} | {r['english']['recall@5']:.3f} | "
            f"{r['roman_urdu']['recall@5']:.3f} | {r['all']['mrr']:.3f} | {r['ms_per_query']:.1f} |"
        )
    return head + "\n".join(rows)


def update_benchmark(path, intro, table):
    p = Path(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    block = f"{START}\n{table}\n{END}"
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip() + f"\n\n## Week 4: hybrid search and reranking\n\n{intro}\n\n{block}\n"
    p.write_text(text, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--depth", type=int, default=20, help="how many results each retriever gives to RRF")
    ap.add_argument("--rerank-model", default="cross-encoder/ms-marco-MiniLM-L-6-v2", help="'none' to skip")
    ap.add_argument("--out", default="eval/week4_results.json")
    ap.add_argument("--bench", default="docs/benchmark.md")
    a = ap.parse_args(argv)

    chunks = build_chunks(load_docs(a.raw_dir), "heading")
    questions = load_questions(a.questions)

    bm25 = BM25Index(chunks)
    print("loading", MODELS["e5-small"]["name"], flush=True)
    e5 = VectorIndex(chunks, Embedder("e5-small"))
    print("loading", MODELS["minilm"]["name"], flush=True)
    minilm = VectorIndex(chunks, Embedder("minilm"))

    systems = {
        "BM25": bm25,
        "e5-small (vector)": e5,
        "Hybrid BM25 + e5 (rrf_k=60)": HybridIndex([bm25, e5], 60, a.depth),
        "Hybrid BM25 + e5 (rrf_k=10)": HybridIndex([bm25, e5], 10, a.depth),
        "Hybrid BM25 + MiniLM (rrf_k=60)": HybridIndex([bm25, minilm], 60, a.depth),
        "Hybrid BM25 + e5 + MiniLM (rrf_k=60)": HybridIndex([bm25, e5, minilm], 60, a.depth),
    }
    if a.rerank_model.lower() != "none":
        print("loading reranker", a.rerank_model, flush=True)
        systems["Hybrid BM25 + e5 + rerank"] = RerankIndex(
            HybridIndex([bm25, e5], 60, a.depth), a.rerank_model, pool=a.depth
        )

    results, misses = {}, {}
    for name, index in systems.items():
        t0 = time.perf_counter()
        ranks = first_ranks(index, questions, a.k)
        ms = (time.perf_counter() - t0) * 1000 / len(questions)
        results[name] = summarise(questions, ranks)
        results[name]["ms_per_query"] = round(ms, 1)
        misses[name] = [_first(q, Q_KEYS) for q, r in zip(questions, ranks) if r is None or r > 5]

    table = markdown_table(results)
    print(table)
    best = max(results, key=lambda n: (results[n]["all"]["recall@5"], results[n]["all"]["mrr"]))
    print("\nBest by recall@5, then MRR:", best)

    n = results["BM25"]
    intro = (
        f"{len(questions)} questions ({n['english']['n']} English, {n['roman_urdu']['n']} Roman Urdu), "
        f"{len(chunks)} heading chunks. RRF fuses the top {a.depth} of each retriever. "
        f"ms / query includes searching the top {a.k} (vector systems also embed the query)."
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(
        json.dumps({"chunks": len(chunks), "k": a.k, "depth": a.depth, "results": results,
                    "misses_at_5": misses}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    update_benchmark(a.bench, intro, table)
    return results


if __name__ == "__main__":
    main()
