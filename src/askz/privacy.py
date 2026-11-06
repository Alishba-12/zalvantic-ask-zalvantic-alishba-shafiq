"""Remove personal details from a question before it is logged."""
import re

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[link]"),
    (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[number]"),
    (re.compile(r"\b\d{5,}\b"), "[number]"),
]


def anonymise(text: str, max_len: int = 300) -> str:
    for pattern, tag in _PATTERNS:
        text = pattern.sub(tag, text)
    return " ".join(text.split())[:max_len]
