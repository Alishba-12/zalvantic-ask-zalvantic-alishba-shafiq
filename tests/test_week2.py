import pytest

from askz.chunking import build_chunks, chunk_by_heading, chunk_fixed
from askz.evaluate import hit_at_k, is_relevant
from askz.search import BM25Index, tokenize

DOC = """# Company
Zalvantic builds software.

## AI and Automation
We build chatbots and RAG assistants for clients.

## Web Backend
We build FastAPI backends and databases.
