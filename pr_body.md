## Week 2: Split the knowledge into chunks and search it with BM25

### Summary
This week I split the Zalvantic knowledge base into chunks in two ways: by heading and by fixed size (120 words with 30 words of overlap). I built a BM25 index on top of the chunks and wrote an evaluation script that measures hit@3 on the 44 questions in eval/questions.json. I also added noise filtering and duplicate removal so menu text and repeated paragraphs do not pollute the index. The chunks are saved in data/processed/chunks.jsonl.

### How to run or test it
```bash
pip install -r requirements.txt
PYTHONPATH=src python -m pytest -v
PYTHONPATH=src python -m askz.evaluate
```
Results are written to eval/week2_results.json.

### Screenshots or demo
| Strategy | Chunks | hit@3 |
|---|---|---|
| By heading | HEAD_CHUNKS | HEAD_SCORE |
| Fixed size + overlap | FIXED_CHUNKS | FIXED_SCORE |

### "Done when" checklist
- [x] Chunking by heading is implemented
- [x] Fixed-size chunking with overlap is implemented
- [x] BM25 search returns the top k chunks
- [x] hit@3 is compared for both strategies on the question set
- [ ] All tests pass
- [ ] Benchmark notes added in docs/benchmark.md

### AI tools used
I used Colab's Gemini assistant to help with the chunking code, the test fixes and the repo cleanup. I checked the outputs myself by running pytest and the evaluation script, and by reading the misses in eval/week2_results.json.

### What I learned, and what is still unclear
I learned that heading chunks keep each answer together and gave the better hit@3, while fixed windows sometimes cut an answer in half. Roman Urdu questions are still weak because BM25 only matches exact words. I am still not fully clear on how BM25 length normalization affects short chunks, and I want to read more about it.
