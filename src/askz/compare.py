"""Week 3: compare BM25 with two embedding models using recall@5 and MRR."""
import argparse
import json
from pathlib import Path

from .chunking import build_chunks, load_docs
from .embed import MODELS, Embedder, VectorIndex
from .evaluate import Q_KEYS, _first, load_questions
from .evaluate import is_relevant
from .search import BM25Index

START, END = "<!-- week3-table:start -->", "<!-- week3-table:end -->"


def first_ranks(index, questions, k=10):
    """For every question: 1-based rank of the first relevant chunk in the top k, or None."""
    ranks = []
    for q in questions:
        top = index.search(_first(q, Q_KEYS), k=k)
        ranks.append(next((i for i, (c, _) in enumerate(top, 1) if is_relevant(c, q)), None))
    return ranks


def recall_at(ranks, n=5):
    return sum(1 for r in ranks if r is not None and r <= n) / len(ranks) if ranks else 0.0


def mrr(ranks):
    return sum(1 / r for r in ranks if r) / len(ranks) if ranks else 0.0


def summarise(questions, ranks):
    groups = {
        "all": lambda q: True,
        "english": lambda q: q.get("language", "en") == "en",
        "roman_urdu": lambda q: q.get("language", "en") != "en",
    }
    out = {}
    for name, keep in groups.items():
        rs = [r for q, r in zip(questions, ranks) if keep(q)]
        out[name] = {"n": len(rs), "recall@5": round(recall_at(rs, 5), 4), "mrr": round(mrr(rs), 4)}
    return out


def markdown_table(results):
    lines = [
        "| System | All R@5 | All MRR | English R@5 | English MRR | Roman Urdu R@5 | Roman Urdu MRR |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        a, e, u = r["all"], r["english"], r["roman_urdu"]
        lines.append(
            f"| {name} | {a['recall@5']:.3f} | {a['mrr']:.3f} | {e['recall@5']:.3f} | "
            f"{e['mrr']:.3f} | {u['recall@5']:.3f} | {u['mrr']:.3f} |"
        )
    return "\n".join(lines)


def update_benchmark(path, intro, table):
    """Rewrite only the block between the markers, so notes written by hand survive a rerun."""
    p = Path(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    block = f"{START}\n{intro}\n\n{table}\n{END}"
    if START in text and END in text:
        pre, rest = text.split(START, 1)
        _, post = rest.split(END, 1)
        text = pre + block + post
    else:
        text = text.rstrip() + "\n\n## Week 3: search by meaning\n\n" + block + "\n"
    p.write_text(text, encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--k", type=int, default=10, help="how deep to search; MRR is measured inside this depth")
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--out", default="eval/week3_results.json")
    ap.add_argument("--bench", default="docs/benchmark.md")
    a = ap.parse_args(argv)

    chunks = build_chunks(load_docs(a.raw_dir), "heading")
    questions = load_questions(a.questions)
    systems = {"BM25": BM25Index(chunks)}
    for key in a.models:
        print("loading", MODELS[key]["name"], flush=True)
        systems[MODELS[key]["label"]] = VectorIndex(chunks, Embedder(key))

    results, misses = {}, {}
    for name, index in systems.items():
        ranks = first_ranks(index, questions, a.k)
        results[name] = summarise(questions, ranks)
        misses[name] = [_first(q, Q_KEYS) for q, r in zip(questions, ranks) if r is None or r > 5]

    table = markdown_table(results)
    n = results["BM25"]
    intro = (
        f"{len(questions)} questions ({n['english']['n']} English, {n['roman_urdu']['n']} Roman Urdu), "
        f"{len(chunks)} heading chunks, same chunks for every system. "
        f"R@5 = share of questions with a relevant chunk in the top 5. "
        f"MRR = mean of 1/rank of the first relevant chunk (searching the top {a.k}, 0 if not found)."
    )
    print(table)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(
        json.dumps({"chunks": len(chunks), "k": a.k, "results": results, "misses_at_5": misses},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    update_benchmark(a.bench, intro, table)
    return results


if __name__ == "__main__":
    main()
