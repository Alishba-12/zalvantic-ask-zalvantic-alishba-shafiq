"""Glue between the API and the pipeline from weeks 1 to 6."""
import json
import os
from groq import Groq

from .guardrails import check_input, check_output
from .generate import SYSTEM_PROMPT, REFUSAL, build_prompt, cited_ids, search_query
from .hybrid import final_index

MODEL = "openai/gpt-oss-120b"
CHUNKS_PATH = "data/processed/chunks.jsonl"
_retriever = None


def _as_dict(c):
    if isinstance(c, dict):
        d = dict(c)
    else:
        d = dict(vars(c))
    d.setdefault("text", getattr(c, "text", ""))
    if "source" not in d:
        d["source"] = next((d[k] for k in ("path", "file", "doc", "url", "title") if k in d), "unknown")
    return d


def _get_retriever():
    """Build the week 4 hybrid index once and wrap it as retriever(query, k) -> list of chunk dicts."""
    global _retriever
    if _retriever is None:
        from types import SimpleNamespace

        with open(CHUNKS_PATH, encoding="utf-8") as f:
            chunks = [SimpleNamespace(**json.loads(line)) for line in f if line.strip()]
        idx = final_index(chunks)
        fn = next((getattr(idx, n) for n in ("search", "retrieve", "query") if hasattr(idx, n)), idx)

        def retriever(q, k):
            out = fn(q, k)
            return [_as_dict(r[0] if isinstance(r, (tuple, list)) else r) for r in out]

        _retriever = retriever
    return _retriever


def stream_answer(question: str):
    """Yields ("token", text), ("replace", text), ("sources", [..]) and finally ("outcome", str)."""
    v = check_input(question)
    if v.blocked:
        yield ("token", v.message)
        yield ("sources", [])
        yield ("outcome", "refused")
        return

    chunks = _get_retriever()(search_query(question), 5)
    if not chunks:
        yield ("token", REFUSAL)
        yield ("sources", [])
        yield ("outcome", "unanswered")
        return

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    stream = client.chat.completions.create(
        model=MODEL, stream=True,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": build_prompt(question, chunks)}],
    )
    parts = []
    for part in stream:
        piece = part.choices[0].delta.content or ""
        if piece:
            parts.append(piece)
            yield ("token", piece)
    text = "".join(parts).strip()

    # Week 6 output filter runs after streaming, so if it fires we replace the text on screen
    out = check_output(text)
    if out.blocked:
        yield ("replace", out.message)
        yield ("sources", [])
        yield ("outcome", "refused")
        return

    ids = cited_ids(text, len(chunks))
    if REFUSAL.lower() in text.lower() or not ids:
        yield ("replace", REFUSAL)  # same rule as week 5: no valid citation, no answer
        yield ("sources", [])
        yield ("outcome", "unanswered")
        return

    yield ("sources", [f"[{i}] {chunks[i - 1].get('source', 'unknown')}" for i in ids])
    yield ("outcome", "answered")
