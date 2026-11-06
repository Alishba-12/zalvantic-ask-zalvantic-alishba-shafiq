from askz import generate as G

def fake_chunks(q, k=5):
    return [{"text": "Zalvantic builds chatbots.", "source": "services.md"}]

def test_normalise_roman_urdu():
    assert "qeemat" in G.normalise_query("Aap ki keemat kia hy?")
    assert "price" in G.search_query("Aapki keemat kitni hai?")

def test_prompt_has_numbered_chunks():
    p = G.build_prompt("What do you do?", fake_chunks("x"))
    assert "[1] (source: services.md)" in p

def test_answer_with_citation_lists_sources():
    res = G.answer("What do you build?", fake_chunks, lambda s, u: "Zalvantic builds chatbots [1].")
    assert res["sources"] == ["[1] services.md"]

def test_answer_without_citation_is_refused():
    res = G.answer("What do you build?", fake_chunks, lambda s, u: "Zalvantic builds chatbots.")
    assert res["answer"] == G.REFUSAL and not res["grounded"]

def test_bad_citation_number_is_refused():
    res = G.answer("q", fake_chunks, lambda s, u: "Something [7].")
    assert res["answer"] == G.REFUSAL

def test_refusal_and_no_chunks():
    assert G.answer("q", fake_chunks, lambda s, u: "I don't have that information")["sources"] == []
    assert G.answer("q", lambda q, k: [], lambda s, u: "x")["answer"] == G.REFUSAL
