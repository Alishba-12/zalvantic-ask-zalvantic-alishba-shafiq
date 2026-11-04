# Ask Zalvantic

An AI sales and support assistant for Zalvantic. It answers client questions in English and Roman Urdu, always with a source. This is built week by week as part of my internship. Right now only week 1 is done: the knowledge base and a simple command line search.

## Folder layout

```
ask-zalvantic/
├── data/raw/          source text collected from zalvantic.com + my own notes (Markdown)
├── data/processed/    cleaned paragraph chunks (JSONL)
├── eval/questions.json   40+ client questions with expected sources (10+ in Roman Urdu)
├── src/askz/
│   ├── ingest.py      downloads public pages, saves clean Markdown     (week 1)
│   ├── chunk.py       removes duplicates and menu text, writes JSONL   (week 1)
│   ├── bm25.py        command line search, best matching paragraph     (week 1)
│   ├── embed.py       embeddings                                       (later)
│   ├── retrieve.py    hybrid retrieval                                 (later)
│   ├── generate.py    grounded answers                                 (later)
│   ├── guardrails.py  refuse prices, discounts, legal promises         (later)
│   └── api.py         FastAPI service                                  (later)
├── widget/            chat.js and demo.html                            (later)
├── tests/
├── docs/benchmark.md
├── Dockerfile, docker-compose.yml, .env.example
└── README.md
```

## Run it (week 1)

```bash
pip install -r requirements.txt

# 1. collect the public pages as Markdown into data/raw/
PYTHONPATH=src python -m askz.ingest

# 2. clean + split into paragraphs -> data/processed/chunks.jsonl
PYTHONPATH=src python -m askz.chunk

# 3. ask a question
PYTHONPATH=src python -m askz.bm25 "What services does Zalvantic offer?"
PYTHONPATH=src python -m askz.bm25 "Aap kitne din mein project complete karte hain?" --top 3

# 4. check the question file (hit@1 and hit@3)
PYTHONPATH=src python -m askz.bm25 --eval

# tests
PYTHONPATH=src python -m pytest -q
```

## Notes

- Only public pages are used, robots.txt is respected, and requests are slow and polite.
- `data/raw/notes-services.md` is written by me in my own words from public sources.
- Search is keyword based (BM25), so Roman Urdu questions only work when the same words appear in the text. Embeddings come in week 3.
