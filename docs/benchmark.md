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
- No system wins everywhere. BM25 is better with exact words and e5 is better at ranking by meaning, so a hybrid of the two (Week 4) is the natural next step.
