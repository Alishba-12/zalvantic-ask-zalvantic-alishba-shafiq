"""Tests for week 1: cleaning, chunking, search, and the question file.

Run from the repo root:  PYTHONPATH=src python -m pytest -q
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from askz.bm25 import BM25  # noqa: E402
from askz.chunk import build_chunks, is_noise  # noqa: E402
from askz.ingest import find_links, html_to_markdown, slugify  # noqa: E402

QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "questions.json"

HTML = """
<html><head><title>Services | Test Co</title></head><body>
<nav><a href="/about">About</a><a href="/services">Services</a></nav>
<main>
  <h1>AI and Automation</h1>
  <p>We build chatbots and automate repetitive business work for small teams.</p>
  <p>We build chatbots and automate repetitive business work for small teams.</p>
  <ul><li>Chatbots</li><li>Workflow automation</li></ul>
</main>
<footer>All rights reserved</footer>
<script>var x = 1;</script>
</body></html>
"""


def test_html_to_markdown_removes_menu_footer_and_duplicates():
    md = html_to_markdown(HTML, "https://test.co/services")
    assert "All rights reserved" not in md
    assert "var x" not in md
    assert md.count("We build chatbots") == 1
    assert "- Chatbots" in md and "Source: https://test.co/services" in md


def test_slugify_and_links():
    assert slugify("https://test.co/") == "home"
    assert slugify("https://test.co/Services/AI") == "services-ai"
    html = '<a href="/a#x">a</a><a href="mailto:x@y.z">m</a><a href="https://other.com">o</a><a href="/logo.png">i</a>'
    assert find_links(html, "https://test.co", "test.co") == ["https://test.co/a"]


def test_noise_rules():
    assert is_noise("Contact us")
    assert not is_noise("hello@test.co")


def test_chunking_dedupes_and_search_finds_paragraph(tmp_path):
    (tmp_path / "a.md").write_text(
        "# A\n\nSource: https://t.co/a\n\n## Services\n\n"
        "We build chatbots and automate repetitive business work for small teams.\n\n"
        "Home\n\n## Contact\n\nYou can email our team any time at hello@t.co for a free call.\n",
        encoding="utf-8")
    (tmp_path / "b.md").write_text(
        "# B\n\nSource: https://t.co/b\n\n## Services\n\n"
        "We build chatbots and automate repetitive business work for small teams.\n\n"
        "Our web team builds custom backend APIs using Python and FastAPI for clients.\n",
        encoding="utf-8")
    chunks = build_chunks(tmp_path)
    assert len(chunks) == 3  # duplicate paragraph and "Home" removed
    index = BM25(chunks)
    best = index.search("How can I email the team?", top=1)[0][1]
    assert "hello@t.co" in best["text"]
    best = index.search("Aap backend API kaise banate hain?", top=1)[0][1]
    assert "FastAPI" in best["text"]


def test_questions_file_has_40_plus_and_10_roman_urdu():
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    assert len(questions) >= 40
    assert sum(q["language"] == "roman_ur" for q in questions) >= 10
    assert len({q["id"] for q in questions}) == len(questions)
    assert all(q["question"].strip() and "expected_source" in q for q in questions)
