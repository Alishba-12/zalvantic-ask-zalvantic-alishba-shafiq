# Week 2 benchmark: chunking strategies with BM25

44 questions, 31 documents. A hit means one of the top 3 chunks comes from the expected page and contains an expected keyword.

| Strategy | Chunks | hit@3 |
|---|---|---|
| By heading | 296 | 0.818 |
| Fixed size (120 words, 30 overlap) | 119 | 0.750 |

Heading chunks win. Each section keeps one topic together, while a fixed window can cut an answer in half or mix two topics. Fixed chunks missed questions about project examples, RAG systems and CMS integration that heading chunks found.
Both strategies miss the same 7 questions (support after launch, code ownership, reply time, REST and GraphQL APIs, and some Roman Urdu ones). BM25 only matches exact words, so these need embeddings in Week 3.
