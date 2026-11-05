# Week 2 benchmark: chunking strategies with BM25

44 questions, 31 documents. A hit means one of the top 3 chunks comes from the expected page and contains an expected keyword.

| Strategy | Chunks | hit@3 |
|---|---|---|
| By heading | 296 | 0.818 |
| Fixed size (120 words, 30 overlap) | 119 | 0.750 |

Heading chunks win. Each section keeps one topic together, while a fixed window can cut an answer in half or mix two topics. Fixed chunks missed questions about project examples, RAG systems and CMS integration that heading chunks found.
Both strategies miss the same 7 questions (support after launch, code ownership, reply time, REST and GraphQL APIs, and some Roman Urdu ones). BM25 only matches exact words, so these need embeddings in Week 3.

## Week 3: search by meaning

<!-- week3-table:start -->
44 questions (32 English, 12 Roman Urdu), 296 heading chunks, same chunks for every system. R@5 = share of questions with a relevant chunk in the top 5. MRR = mean of 1/rank of the first relevant chunk (searching the top 10, 0 if not found).

| System | All R@5 | All MRR | English R@5 | English MRR | Roman Urdu R@5 | Roman Urdu MRR |
|---|---|---|---|---|---|---|
| BM25 | 0.864 | 0.646 | 0.906 | 0.644 | 0.750 | 0.649 |
| all-MiniLM-L6-v2 | 0.795 | 0.553 | 0.906 | 0.605 | 0.500 | 0.415 |
| multilingual-e5-small | 0.818 | 0.653 | 0.875 | 0.696 | 0.667 | 0.540 |
<!-- week3-table:end -->

### What the numbers say

- BM25 is still very strong here. It has the best recall@5 overall (0.864) and the best Roman Urdu scores (0.750 recall@5, 0.649 MRR). This is probably because many questions share exact words with the pages, and the Roman Urdu questions still contain English words like website, project and services.
- multilingual-e5-small is the best embedding model. Its MRR (0.653) is slightly above BM25 overall and higher on English questions (0.696 against 0.644), so it tends to put the right chunk higher. Its recall@5 is a little lower (0.818), so it finds fewer right chunks in total.
- all-MiniLM-L6-v2 matches BM25 on English recall@5 (0.906) but ranks the right chunk lower (MRR 0.605 against 0.644).
- Roman Urdu is where the models differ most. MiniLM finds the right chunk in the top 5 for 6 of 12 questions (0.500), e5 for 8 of 12 (0.667) and BM25 for 9 of 12 (0.750). Roman Urdu is Urdu written in English letters, so neither model has seen much of it in training. e5 copes better because it was trained on many languages.
- There are only 12 Roman Urdu questions and 44 in total, so one question moves the Roman Urdu score by about 8 points. A gap of one or two questions should not be read as a real difference.
- The systems miss different questions. BM25 misses 3 that e5 finds (the REST and GraphQL APIs question and two Roman Urdu ones), e5 misses 5 that BM25 finds (3 of them in Roman Urdu), and 3 questions are missed by both (support after launch, and reply time in English and Roman Urdu). The ones e5 misses probably contain exact words like chatbot, automate and WhatsApp, which BM25 matches directly.
- No system wins everywhere. BM25 is better with exact words and e5 is better at ranking by meaning, so a hybrid of the two (Week 4) is the natural next step.

## Week 4: hybrid search and reranking

44 questions (32 English, 12 Roman Urdu), 296 heading chunks. RRF fuses the top 20 of each retriever. ms / query includes searching the top 10 (vector systems also embed the query).

<!-- week4-table:start -->
| System | R@5 all | R@5 English | R@5 Roman Urdu | MRR all | ms / query |
|---|---|---|---|---|---|
| BM25 | 0.864 | 0.906 | 0.750 | 0.646 | 1.6 |
| e5-small (vector) | 0.818 | 0.875 | 0.667 | 0.653 | 59.7 |
| Hybrid BM25 + e5 (rrf_k=60) | 0.864 | 0.906 | 0.750 | 0.649 | 44.8 |
| Hybrid BM25 + e5 (rrf_k=10) | 0.864 | 0.906 | 0.750 | 0.658 | 41.0 |
| Hybrid BM25 + MiniLM (rrf_k=60) | 0.886 | 0.938 | 0.750 | 0.596 | 22.6 |
| Hybrid BM25 + e5 + MiniLM (rrf_k=60) | 0.818 | 0.906 | 0.583 | 0.644 | 61.5 |
| Hybrid BM25 + e5 + rerank | 0.909 | 0.906 | 0.917 | 0.549 | 2136.6 |
<!-- week4-table:end -->


### Final choice

I am going with **Hybrid BM25 + multilingual-e5-small, RRF with rrf_k=10 and depth 20**.

| Setup | R@5 | MRR | ms / query |
|---|---|---|---|
| BM25 alone | 0.864 | 0.646 | 1.6 |
| e5-small alone | 0.818 | 0.653 | 59.7 |
| **Hybrid BM25 + e5 (rrf_k=10)** | **0.864** | **0.658** | **41.0** |
| Hybrid BM25 + e5 + rerank | 0.909 | 0.549 | 2136.6 |

Recall@5 is 0.864, so the 0.80 target is reached.

Why this one:
- Hybrid keeps the BM25 recall (0.864) and has the best MRR of the fast setups (0.658), so the right chunk lands higher in the list.
- Roman Urdu stays at 0.750, the same as BM25, while the vector side helps when a question does not share exact words with the chunk.
- It costs about 41 ms per query, which is fine for a chatbot.

Why not the others:
- The cross-encoder reranker (ms-marco-MiniLM) gave the best recall (0.909) but the MRR fell from 0.658 to 0.549 and it took around 2.1 seconds per query. That is far too slow for streaming answers, and the model is trained on English only.
- BM25 + MiniLM reached 0.886 recall but its MRR is only 0.596, and Roman Urdu did not improve.
- Adding both embedding models together (0.818) was worse, so more retrievers is not always better.

Honest caveat: there are only 44 questions, so one question is about 2.3 points. The differences between the top setups are 1 to 2 questions and could be noise. I would check this again once the knowledge base grows.
