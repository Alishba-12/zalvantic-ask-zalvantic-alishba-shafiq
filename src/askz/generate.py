"""Week 5: grounded answer generation (answers only from retrieved chunks)."""
import re

REFUSAL = "I don't have that information"

# Common Roman Urdu spelling variants -> one spelling
CANON = {
    "kia": "kya", "kiya": "kya", "hy": "hai", "nhi": "nahi", "nahin": "nahi", "nai": "nahi",
    "krta": "karta", "krte": "karte", "krti": "karti", "kr": "kar", "krain": "karain", "krna": "karna",
    "bnana": "banana", "bnata": "banata", "bnate": "banate", "bnwana": "banwana",
    "kesy": "kaise", "kese": "kaise", "kaisay": "kaise", "kaisey": "kaise",
    "kiu": "kyun", "kyu": "kyun", "kun": "kyun", "konsi": "kaunsi", "konsa": "kaunsa", "kon": "kaun",
    "kidhr": "kahan", "kahn": "kahan", "keemat": "qeemat", "kimat": "qeemat", "kmt": "qeemat",
    "rabtah": "rabta", "khidmaat": "khidmat", "apka": "aapka", "apki": "aapki", "apke": "aapke",
    "ap": "aap", "kitny": "kitne", "kb": "kab", "kam": "kaam",
}

# Roman Urdu word -> English keywords added to the SEARCH query only (the LLM still sees the original question)
EXPAND = {
    "qeemat": "price cost", "rabta": "contact", "khidmat": "services", "kaam": "work",
    "banwana": "build", "banana": "build", "tareeqa": "process", "muddat": "timeline duration",
    "kitna": "how much", "kitne": "how many", "kitni": "how much", "kaun": "who", "kahan": "where",
    "kab": "when", "madad": "help",
}


def normalise_query(q):
    """Lowercase, strip punctuation, fix common Roman Urdu spellings."""
    q = re.sub(r"[^\w\s]", " ", q.lower())
    words = [CANON.get(w, w) for w in q.split()]
    return " ".join(words)


def search_query(q):
    """Normalised query plus English keywords for Roman Urdu words. Use this for retrieval."""
    norm = normalise_query(q)
    extra = [EXPAND[w] for w in norm.split() if w in EXPAND]
    return (norm + " " + " ".join(extra)).strip()


SYSTEM_PROMPT = f"""You are Ask Zalvantic, an assistant that answers questions about Zalvantic.
Rules:
1. Use ONLY the numbered context chunks below. Never use outside knowledge and never guess.
2. After every sentence that uses a chunk, add its number like [1] or [2][3].
3. If the context does not clearly answer the question, reply with exactly: {REFUSAL}
4. Never state prices, discounts, deadlines or legal promises unless a chunk states them word for word.
5. Reply in the language of the question (English or Roman Urdu). Keep it short and simple.
"""


def build_context(chunks):
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] (source: {c.get('source', 'unknown')})\n{c['text']}")
    return "\n\n".join(parts)


def build_prompt(question, chunks):
    return f"Context:\n{build_context(chunks)}\n\nQuestion: {question}\nAnswer:"


def cited_ids(answer, n_chunks):
    ids = [int(x) for x in re.findall(r"\[(\d+)\]", answer)]
    return sorted({i for i in ids if 1 <= i <= n_chunks})


def answer(question, retriever, llm, k=5):
    """retriever(query, k) -> list of {"text", "source"}; llm(system, user) -> str."""
    chunks = retriever(search_query(question), k)
    if not chunks:
        return {"question": question, "answer": REFUSAL, "sources": [], "grounded": True}
    raw = llm(SYSTEM_PROMPT, build_prompt(question, chunks)).strip()
    if REFUSAL.lower() in raw.lower():
        return {"question": question, "answer": REFUSAL, "sources": [], "grounded": True}
    ids = cited_ids(raw, len(chunks))
    if not ids:  # an answer without a valid citation is not allowed
        return {"question": question, "answer": REFUSAL, "sources": [], "grounded": False}
    sources = [f"[{i}] {chunks[i - 1].get('source', 'unknown')}" for i in ids]
    return {"question": question, "answer": raw, "sources": sources, "grounded": True}


def format_answer(res):
    if not res["sources"]:
        return res["answer"]
    return res["answer"] + "\n\nSources:\n" + "\n".join(res["sources"])
